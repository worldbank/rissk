from src.item_processing import *
from src.utils.stats_utils import *
from src.detection_algorithms import *
from scipy import stats
from sklearn.preprocessing import StandardScaler, MinMaxScaler, RobustScaler, Normalizer, PowerTransformer
from sklearn.decomposition import PCA


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

            if feature_name in self._allowed_features and self._score_columns is None:
                try:
                    print('Processing Score {}...'.format(feature_name))
                    getattr(self, method_name)(feature_name)
                    # print('Score{} Processed'.format(feature_name))
                except Exception as e:
                    print("ERROR ON FEATURE SCORE: {}, It won't be used in further calculation".format(feature_name))

        score_columns = [col for col in self._df_unit if
                         col.startswith('s__')]  # and col.replace('s__','f__') in  self._allowed_features]
        # Remove columns with only nan or constant values
        self._score_columns = self._df_unit[score_columns].columns[self._df_unit[score_columns].nunique() > 1].tolist()
        return self._df_unit[['interview__id', 'responsible', 'survey_name', 'survey_version', ] + self._score_columns]

    def make_global_score(self):
        scaler = StandardScaler()
        df = self.df_unit_score[self._score_columns]
        df = windsorize_95_percentile(df)# .astype(float).apply(adjustable_winsorize)
        df = pd.DataFrame(scaler.fit_transform(df), columns=self._score_columns)
        pca = PCA(n_components=0.99, whiten=True, random_state=42)

        # Conduct PCA
        df_pca = pca.fit_transform(df.fillna(0))
        scaler = MinMaxScaler(feature_range=(0, 100))
        self._df_unit['unit_risk_score'] = (df_pca * pca.explained_variance_ratio_).sum(axis=1)

        self._df_unit['unit_risk_score'] = scaler.fit_transform(self._df_unit[['unit_risk_score']])

    def save(self):
        # TODO reduce decimal points to first digit
        df = self._df_unit[['interview__id', 'responsible', 'unit_risk_score']].copy()
        df.sort_values('unit_risk_score', inplace=True)
        file_name = "_".join([self.config.surveys[0], self.config.survey_version[0], 'unit_risk_score']) + ".csv"
        output_path = self.config.output_file.split('.')[0] + '.csv'
        df.to_csv(output_path, index=False)
        print(f'SUCCESS! you can find the unit_risk_score output file in {self.config.data.results}')

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
        self._df_unit[score_name] = self._df_unit['responsible'].map(data[score_name])
        # Fill with 0's for missing values
        self._df_unit[score_name].fillna(0, inplace=True)

    def make_score_unit__multi_option_question(self, feature_name):
        data = self.make_score__multi_option_question()
        selected_columns = [col for col in data.columns if feature_name.replace('f__', '__') in col]
        data['total'] = data[selected_columns].mean(1)
        data['total'] = data.drop(columns=['responsible']).mean(1)
        entropy_ = data.groupby('responsible')['total'].mean()

        self._df_unit[feature_name.replace('f__', 's__')] = self._df_unit['responsible'].map(entropy_)

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
        self._df_unit[score_name] = self._df_unit['responsible'].map(data)
        # Fill with 0's for missing values
        self._df_unit[score_name].fillna(0, inplace=True)

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
        data = data.groupby(['interview__id']).agg({score_name: 'mean'})

        self._df_unit[score_name] = self._df_unit['interview__id'].map(data[score_name])
        # Fill with 0's for missing values. It means "No anomalies detected"
        self._df_unit[score_name].fillna(0, inplace=True)

    def make_score_unit__sequence_jump(self, feature_name):
        score_name = feature_name.replace('f__', 's__')
        data = self.make_score__sequence_jump()
        data = data.groupby(['interview__id']).agg({score_name: 'mean'})

        self._df_unit[score_name] = self._df_unit['interview__id'].map(data[score_name])
        # Fill with 0's for missing values. It means "No anomalies detected"
        self._df_unit[score_name].fillna(0, inplace=True)

    def make_score_unit__time_changed(self, feature_name):
        score_name = self.rename_feature(feature_name)
        # Bin the negative time changed into 4 bins:
        # Not time changed, less than one hour, 1-5 hours, 5-24 hours, 24+ hours

        bins = [float('-inf'), -24 * 3600, -5 * 3600, -1 * 3600, -0.1, float('inf')]
        labels = [1, 0.75, 0.5, 0.25, 0]  # Numeric values for each bin
        self._df_unit[score_name] = pd.cut(self._df_unit['f__time_changed'], bins=bins, labels=labels).astype(float)

    def make_score_unit__total_duration(self, feature_name):
        score_name = self.rename_feature(feature_name)
        # transform Total duration into 10 minutes values
        self._df_unit[feature_name] = round(self._df_unit[feature_name] / (3600 / 6)) /self._df_unit['f__number_answered']
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

    def make_score_unit__days_from_start(self, feature_name):
        score_name = self.rename_feature(feature_name)
        self._df_unit[score_name] = (self._df_unit[feature_name] / 7).astype(int)

    def make_score_unit__total_elapse(self, feature_name):
        score_name = self.rename_feature(feature_name)
        self._df_unit[score_name] = (self._df_unit[feature_name] - self._df_unit[feature_name].mean()) / self._df_unit[
            feature_name].std()

    def make_score_unit__pause_duration(self, feature_name):
        score_name = self.rename_feature(feature_name)
        # transform Pause duration into two-hours values for the first day and day value after the first day

        duration_mask = ~pd.isnull(self._df_unit[feature_name])

        self._df_unit.loc[duration_mask, feature_name] = round(self._df_unit[duration_mask][feature_name] / (3600 * 2),
                                                               0)
        self._df_unit.loc[duration_mask, feature_name] = self._df_unit[duration_mask][feature_name].apply(
            lambda x: round(x / 12) * 12 if x > 12 else x)

        # Find anomalies in the distribution making use of COF anomaly detector.
        # Connectivity-Based Outlier Factor (COF) COF uses the ratio of average chaining distance
        # of data point and the average of average chaining distance of k nearest neighbor
        # of the data point, as the outlier score for observations.
        contamination = self.get_contamination_parameter(feature_name, method='savgol', random_state=42)
        model = COF(contamination=contamination)
        model.fit(self._df_unit[duration_mask][[feature_name]])
        self._df_unit.loc[duration_mask, score_name] = model.predict(self._df_unit[duration_mask][[feature_name]])
        # Fill with 0's for missing values. It means "No anomalies detected"
        self._df_unit[score_name].fillna(1, inplace=True)

    def make_score_unit__pause_count(self, feature_name):
        score_name = self.rename_feature(feature_name)
        pause_mask = ~pd.isnull(self._df_unit[feature_name])

        contamination = self.get_contamination_parameter(feature_name, method='medfilt', random_state=42)

        model = ECOD(contamination=contamination)
        model.fit(self._df_unit[pause_mask][[feature_name]])
        self._df_unit.loc[pause_mask, score_name] = model.predict(self._df_unit[pause_mask][[feature_name]])

        score_name1 = score_name + '_lower'
        score_name2 = score_name + '_upper'
        min_good_value = self._df_unit[(self._df_unit[score_name] == 0) & pause_mask][feature_name].min()
        max_good_value = self._df_unit[(self._df_unit[score_name] == 0) & pause_mask][feature_name].max()

        self._df_unit[score_name1] = 0
        self._df_unit[score_name2] = 0

        self._df_unit.loc[(self._df_unit[feature_name] < min_good_value) & pause_mask, score_name1] = 1
        self._df_unit.loc[(self._df_unit[feature_name] > max_good_value) & pause_mask, score_name2] = 1

        self._df_unit.drop(columns=[score_name], inplace=True)
        self._df_unit[score_name1].fillna(1, inplace=True)
        self._df_unit[score_name2].fillna(0, inplace=True)

    def make_score_unit__number_answered(self, feature_name):
        score_name = self.rename_feature(feature_name)
        # self._df_unit[score_name] = (self._df_unit[feature_name] - self._df_unit[feature_name].mean()) / self._df_unit[
        #     feature_name].std()

    def make_score_unit__number_unanswered(self, feature_name):
        score_name = self.rename_feature(feature_name)
        self._df_unit[score_name] = self._df_unit[feature_name]

    def make_score_unit__gps(self, feature_name):
        data = self.make_score__gps()
        features = ['s__gps_proximity_counts', 's__gps_spatial_outlier']

        data = data.groupby('interview__id')[features].sum()
        data = data.reset_index()

        self._df_unit['s__gps_proximity_counts'] = self._df_unit['interview__id'].map(
            data.set_index('interview__id')['s__gps_proximity_counts']
        )

        self._df_unit['s__gps_spatial_outlier'] = self._df_unit['interview__id'].map(
            data.set_index('interview__id')['s__gps_spatial_outlier']
        )

        data = self.df_item.groupby('interview__id')[feature_name].sum()
        data = data.reset_index()
        score_name = feature_name.replace('f__', 's__')
        self._df_unit[score_name] = self._df_unit['interview__id'].map(
            data.set_index('interview__id')[feature_name]
        )

        self._df_unit['s__gps_proximity_counts'].fillna(0, inplace=True)
        self._df_unit['s__gps_spatial_outlier'].fillna(0, inplace=True)

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
