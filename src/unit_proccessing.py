from src.item_processing import *
from src.detection_algorithms import *
from sklearn.preprocessing import StandardScaler, MinMaxScaler, Normalizer
from sklearn.preprocessing import normalize
# from sklearn.decomposition import PCA
from pyod.models.pca import PCA
from pyod.models.iforest import IForest
from sklearn.impute import SimpleImputer

def windsorize_95_percentile(df):
    """
    Windsorize values in all columns of the DataFrame that are above the 95th percentile.

    Args:
    - df (pd.DataFrame): Input DataFrame

    Returns:
    - pd.DataFrame: Windsorized DataFrame
    """
    for column in df.columns:
        # Calculate the 95th percentile for the column
        percentile_95 = df[column].quantile(0.95)

        # Set values above the 95th percentile to the value at the 95th percentile
        df[column] = df[column].apply(lambda x: min(x, percentile_95))

    return df


class UnitDataProcessing(ItemFeatureProcessing):

    def __init__(self, config):
        super().__init__(config)
        self._score_columns = None

    @property
    def df_unit_score(self):
        for method_name in self.get_make_methods(method_type='score', level='unit'):
            feature_name = method_name.replace('make_score_unit__', 'f__')
            score_name = self.rename_feature(feature_name)
            if feature_name in self._allowed_features and self._score_columns is None:
                try:
                    print('Processing Score {}...'.format(score_name))
                    getattr(self, method_name)(feature_name)
                    # print('Score{} Processed'.format(feature_name))
                except Exception as e:
                    print("WARNING: SCORE: {} won't be used in further calculation".format(score_name))

        score_columns = [col for col in self._df_unit if
                         col.startswith('s__')]  # and col.replace('s__','f__') in  self._allowed_features]
        # Remove columns with only nan or constant values
        self._score_columns = self._df_unit[score_columns].columns[self._df_unit[score_columns].nunique() > 1].tolist()
        return self._df_unit[['interview__id', 'responsible', 'survey_name', 'survey_version', ] + self._score_columns]

    def make_global_score(self, combine_resp_score=True, restricted_columns=None):
        self._df_unit['unit_risk_score'] = 0
        scaler = StandardScaler()
        df = self.df_unit_score[self._score_columns]
        columns = self._score_columns
        if restricted_columns is not None:
            columns = [col for col in self._score_columns if col not in restricted_columns]
        # df = windsorize_95_percentile(self.df_unit_score[columns].copy())
        df = df[columns].copy()
        df = pd.DataFrame(scaler.fit_transform(df), columns=columns)
        model = IForest(random_state=42)
        model.fit(df.fillna(0))
        scaler = MinMaxScaler(feature_range=(0, 100))
        self._df_unit['unit_risk_score'] = model.decision_scores_

        self._df_unit['unit_risk_score'] = windsorize_95_percentile(self.df_unit[['unit_risk_score']].copy())

        self._df_unit['unit_risk_score'] = scaler.fit_transform(self._df_unit[['unit_risk_score']])

        # Merge unit score with responsible score
        if combine_resp_score:
            # Make responsible Score
            self.make_responsible_score(restricted_columns=columns)
            merged_df = self._df_unit.merge(self._df_resp[['responsible', 'responsible_score']], how='left',
                                            on='responsible')
            self._df_unit['unit_risk_score'] = merged_df['unit_risk_score'] * merged_df['responsible_score']

            self._df_unit['unit_risk_score'] = scaler.fit_transform(self._df_unit[['unit_risk_score']])

    # def make_responsible_score(self, restricted_columns):
    #     scaler = StandardScaler()
    #     columns = [col for col in self._df_resp.columns
    #                if col.startswith('responsible') is False and col not in restricted_columns]
    #
    #     self._df_resp = self._df_resp.groupby('responsible')[columns].mean()
    #     self._df_resp = self._df_resp.reset_index()
    #
    #     df_resp = self._df_resp[columns].fillna(0)
    #     # Remove columns with constant values
    #     df_resp = df_resp.loc[:, df_resp.nunique() != 1]
    #     df_resp = pd.DataFrame(scaler.fit_transform(df_resp), columns=df_resp.columns)
    #
    #     model = PCA(random_state=42)
    #     model.fit(df_resp)
    #     self._df_resp['responsible_score'] = model.decision_scores_  # function(df1)
    #     # scaler = MinMaxScaler(feature_range=(0, 1))
    #     # self._df_resp['responsible_score'] = scaler.fit_transform(self._df_resp[['responsible_score']])
    #     self._df_resp['responsible_score'] = normalize(self._df_resp[['responsible_score']], norm='l1', axis=0)

    def make_responsible_score(self, restricted_columns):
        cols = [c for c in self._df_resp.columns
                if not c.startswith('responsible') and c not in restricted_columns]

        # If nothing to compute from, default to neutral weight = 1.0
        if len(cols) == 0:
            self._df_resp['responsible_score'] = 1.0
            return

        self._df_resp = (
            self._df_resp.groupby('responsible', as_index=False)[cols].mean()
        )

        X = self._df_resp[cols].copy()
        X = SimpleImputer(strategy='median').fit_transform(X)
        X = StandardScaler().fit_transform(X)

        model = PCA(random_state=42)
        model.fit(X)

        # Raw decision scores → clean
        raw = pd.Series(model.decision_scores_, index=self._df_resp.index)
        col = raw.to_frame(name='score').replace([np.inf, -np.inf], np.nan).fillna(0.0)

        # If the L1 norm is zero, normalization would yield NaNs → use neutral 1.0
        l1 = np.abs(col.values).sum()
        if l1 == 0:
            self._df_resp['responsible_score'] = 1.0
        else:
            self._df_resp['responsible_score'] = normalize(col, norm='l1', axis=0).ravel()

    def save(self):
        df = self._df_unit[['interview__id', 'responsible', 'unit_risk_score']]  # .copy()
        df['unit_risk_score'] = df['unit_risk_score'].round(2)
        df.sort_values('unit_risk_score', inplace=True)
        #file_name = "_".join([self.config.surveys[0], self.config.survey_version[0], 'unit_risk_score']) + ".csv"
        output_path = self.config['output_file'].split('.')[0] + '.csv'
        df.to_csv(output_path, index=False)
        print(f'SUCCESS! you can find the unit risk score output file in {output_path}')
        if self.config['feature_score']:

            columns = [col for col in self._df_resp.columns if col.startswith('responsible') is False]

            sorted_columns = sorted(self._score_columns + columns)

            merged_df = self._df_unit.merge(self._df_resp, how='left',
                                            on='responsible')

            merged_df = merged_df[['interview__id', 'responsible', 'survey_name', 'survey_version'] + sorted_columns]
            output_path = self.config['output_file'].split('.')[0] + '_feature_score.csv'
            merged_df.to_csv(output_path, index=False)
            print(f'You can find the unit feature score file in {output_path}')

    def make_score_unit__numeric_response(self, feature_name):
        pass

    def make_score_unit__last_digit(self, feature_name):
        pass

    def make_score_unit__single_question(self, feature_name):
        score_name = self.rename_feature(feature_name)
        # single_question is calculated at responsible level
        data = self.make_score__single_question()
        data = data.groupby(['responsible', 'variable_name']).agg({score_name: 'mean'})
        data = data.reset_index()
        data = data.groupby('responsible').agg({score_name: 'mean'})
        self._df_resp[score_name] = self._df_resp['responsible'].map(data[score_name])
        # Fill with 0's for missing values
        self._df_resp[score_name].fillna(0, inplace=True)

    def make_score_unit__multi_option_question(self, feature_name):
        score_name = self.rename_feature(feature_name)
        # multi_option_question is calculated at responsible level
        data = self.make_score__multi_option_question()
        data = data.groupby(['responsible', 'variable_name']).agg({score_name: 'mean'})
        data = data.reset_index()
        data = data.groupby('responsible').agg({score_name: 'mean'})
        self._df_resp[score_name] = self._df_resp['responsible'].map(data[score_name])
        # Fill with 0's for missing values
        self._df_resp[score_name].fillna(0, inplace=True)

    def make_score_unit__answer_hour_set(self, feature_name):
        data = self.make_score__answer_hour_set()
        score_name = self.rename_feature(feature_name)
        # Get the ratio of anomalies per interview__id over the total number of answer set
        data = data.groupby(['interview__id']).agg({score_name: 'mean'})
        self._df_unit[score_name] = self._df_unit['interview__id'].map(data[score_name])

    def make_score_unit__answer_removed(self, feature_name):
        data = self.make_score__answer_removed()
        score_name = self.rename_feature(feature_name)
        data = data.groupby(['interview__id']).agg({score_name: 'mean'})
        self._df_unit[score_name] = self._df_unit['interview__id'].map(data[score_name])
        # Fill with 0's for missing values
        self._df_unit[score_name].fillna(0, inplace=True)

    def make_score_unit__answer_changed(self, feature_name):
        data = self.make_score__answer_changed()
        score_name = self.rename_feature(feature_name)
        # take the max number of anomaly for each question, i.e. 'roster_level' + 'variable_name'
        data = data.groupby(['interview__id']).agg({score_name: 'mean'})
        self._df_unit[score_name] = self._df_unit['interview__id'].map(data[score_name])
        # Fill with 0's for missing values
        self._df_unit[score_name].fillna(0, inplace=True)

    def make_score_unit__answer_position(self, feature_name):
        score_name = self.rename_feature(feature_name)
        # answer_position is calculated at responsible level
        data = self.make_score__answer_position()
        data = data.groupby(['responsible', 'variable_name']).agg({score_name: 'mean'})
        data = data.reset_index()
        data = data.groupby('responsible')[score_name].mean()
        self._df_resp[score_name] = self._df_resp['responsible'].map(data)
        # Fill with 0's for missing values
        self._df_resp[score_name].fillna(0, inplace=True)

    def make_score_unit__answer_selected(self, feature_name):
        score_name = self.rename_feature(feature_name)
        score_name1 = score_name + '_lower'
        score_name2 = score_name + '_upper'
        data = self.make_score__answer_selected()
        data = data.groupby(['interview__id']).agg({score_name1: 'mean', score_name2: 'mean'})
        data = data.reset_index()
        self._df_unit[score_name1] = self._df_unit['interview__id'].map(data.set_index('interview__id')[score_name1])
        self._df_unit[score_name2] = self._df_unit['interview__id'].map(data.set_index('interview__id')[score_name2])
        # Fill with 0's for missing values
        self._df_unit[score_name1].fillna(0, inplace=True)
        self._df_unit[score_name2].fillna(0, inplace=True)

    def make_score_unit__answer_duration(self, feature_name):
        score_name = self.rename_feature(feature_name)
        score_name1 = score_name + '_lower'
        score_name2 = score_name + '_upper'
        data = self.make_score__answer_duration()
        data = data.groupby(['interview__id']).agg({score_name1: 'mean', score_name2: 'mean'})
        data = data.reset_index()
        self._df_unit[score_name1] = self._df_unit['interview__id'].map(data.set_index('interview__id')[score_name1])
        self._df_unit[score_name2] = self._df_unit['interview__id'].map(data.set_index('interview__id')[score_name2])
        # Fill with 0's for missing values
        self._df_unit[score_name1].fillna(0, inplace=True)
        self._df_unit[score_name2].fillna(0, inplace=True)

    def make_score_unit__first_decimal(self, feature_name):
        score_name = self.rename_feature(feature_name)
        data = self.make_score__first_decimal()
        data = data.groupby(['interview__id']).agg({score_name: 'mean'})

        self._df_unit[score_name] = self._df_unit['interview__id'].map(data[score_name])
        # Fill with 0's for missing values. It means "No anomalies detected"
        self._df_unit[score_name].fillna(0, inplace=True)

    def make_score_unit__first_digit(self, feature_name):
        score_name = self.rename_feature(feature_name)
        data = self.make_score__first_digit()
        data = data.groupby(['responsible']).agg({score_name: 'mean'})

        self._df_resp[score_name] = self._df_resp['responsible'].map(data[score_name])
        # Fill with 0's for missing values
        self._df_resp[score_name].fillna(0, inplace=True)

    def make_score_unit__sequence_jump(self, feature_name):
        score_name = feature_name.replace('f__', 's__')
        data = self.make_score__sequence_jump()
        data = data.groupby(['interview__id']).agg({score_name: 'mean'})

        self._df_unit[score_name] = self._df_unit['interview__id'].map(data[score_name])
        # Fill with 0's for missing values. It means "No anomalies detected"
        self._df_unit[score_name].fillna(0, inplace=True)

    def make_score_unit__time_changed(self, feature_name):
        score_name = self.rename_feature(feature_name)
        # round to 10 min
        self._df_unit[score_name] = round(self._df_unit['f__time_changed'].abs()/600)

    def make_score_unit__total_duration(self, feature_name):
        score_name = self.rename_feature(feature_name)
        # transform Total duration into 10 minutes values
        self._df_unit[score_name] = round(self._df_unit[feature_name] / 300)  # / self._df_unit['f__number_answered']

    def make_score_unit__days_from_start(self, feature_name):
        score_name = self.rename_feature(feature_name)
        self._df_unit[score_name] = (self._df_unit[feature_name] / 7).astype(int)

    def make_score_unit__total_elapse(self, feature_name):
        score_name = self.rename_feature(feature_name)
        self._df_unit[feature_name] = round(self._df_unit[feature_name] / 300)
        contamination = self.get_contamination_parameter(feature_name, method='medfilt', random_state=42)

        model = ECOD(contamination=contamination)
        model.fit(self._df_unit[[feature_name]])
        self._df_unit[score_name] = model.predict(self._df_unit[[feature_name]])

        score_name1 = score_name + '_lower'
        score_name2 = score_name + '_upper'
        min_good_value = self._df_unit[(self._df_unit[score_name] == 0)][feature_name].min()
        max_good_value = self._df_unit[(self._df_unit[score_name] == 0)][feature_name].max()

        self._df_unit[score_name1] = 0
        self._df_unit[score_name2] = 0

        self._df_unit.loc[(self._df_unit[feature_name] < min_good_value), score_name1] = 1
        self._df_unit.loc[(self._df_unit[feature_name] > max_good_value), score_name2] = 1

        self._df_unit.drop(columns=[score_name], inplace=True)

    def make_score_unit__pause_duration(self, feature_name):

        score_name = self.rename_feature(feature_name)
        # transform Total duration into 10 minutes values
        self._df_unit[score_name] = self._df_unit[feature_name] / self._df_unit['f__total_elapse']

    def make_score_unit__pause_count(self, feature_name):
        score_name = self.rename_feature(feature_name)
        pause_mask = ~pd.isnull(self._df_unit[feature_name])
        self._df_unit[score_name] = self._df_unit[feature_name] / self._df_unit['f__number_answered']

    def make_score_unit__number_answered(self, feature_name):
        score_name = self.rename_feature(feature_name)
        self._df_unit[score_name] = self._df_unit[feature_name]

    def make_score_unit__number_unanswered(self, feature_name):
        score_name = self.rename_feature(feature_name)
        self._df_unit[score_name] = self._df_unit[feature_name]

    def make_score_unit__gps(self, feature_name):
        data = self.make_score__gps()
        features = ['s__gps_proximity_counts', 's__gps_outlier', 's__gps_extreme_outlier']

        data = data.groupby('interview__id')[features].sum()
        data = data.reset_index()

        self._df_unit['s__gps_proximity_counts'] = self._df_unit['interview__id'].map(
            data.set_index('interview__id')['s__gps_proximity_counts']
        )

        self._df_unit['s__gps_outlier'] = self._df_unit['interview__id'].map(
            data.set_index('interview__id')['s__gps_outlier']
        )
        self._df_unit['s__gps_extreme_outlier'] = self._df_unit['interview__id'].map(
            data.set_index('interview__id')['s__gps_extreme_outlier']
        )

        data = self.df_item.groupby('interview__id')[feature_name].sum()
        score_name = feature_name.replace('f__', 's__')
        self._df_unit[score_name] = self._df_unit['interview__id'].map(data)

        self._df_unit['s__gps_proximity_counts'].fillna(0, inplace=True)
        self._df_unit['s__gps_outlier'].fillna(0, inplace=True)
        self._df_unit['s__gps_extreme_outlier'].fillna(0, inplace=True)

    # def make_feature_unit__comments(self):
    #     columns_to_check = ['f__comments_set', 'f__comment_length']
    #     if any(col not in self._df_unit.columns for col in columns_to_check):
    #         # f__comments_set, f_comment_length
    #         df_unit_comment = self.df_item.groupby('interview__id').agg(
    #             f__comments_set=('f__comments_set', 'sum'),
    #             f__comment_length=('f__comment_length', 'sum')
    #         ).reset_index()
    #
    #         self._df_unit['f__comments_set'] = self._df_unit['interview__id'].map(
    #             df_unit_comment.set_index('interview__id')['f__comments_set']
    #         )
    #
    #         self._df_unit['f__comment_length'] = self._df_unit['interview__id'].map(
    #             df_unit_comment.set_index('interview__id')['f__comment_length']
    #         )
    #
    # def make_feature_unit__number_answers(self):
    #     answer_per_interview_df = self.df_active_paradata.groupby('interview__id').variable_name.nunique()
    #     answer_per_interview_df = answer_per_interview_df.reset_index()
    #     total_questions = self.df_questionaire[self.df_questionaire['type'].str.contains('Question')]['type'].count()
    #     self._df_unit['f__number_answers'] = self.df_item['interview__id'].map(
    #         answer_per_interview_df.set_index('interview__id')['variable_name'] / total_questions)
