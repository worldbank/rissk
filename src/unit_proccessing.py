from src.item_processing import *
from src.detection_algorithms import *
from scipy import stats
from sklearn.preprocessing import StandardScaler, MinMaxScaler
from sklearn.decomposition import PCA


class UnitDataProcessing(ItemFeatureProcessing):

    def __init__(self, config):
        super().__init__(config)
        self._score_columns = None

    # def make_df_unit(self):
    #     # TODO! deal with multiple responsible for same interview, i.e microdata does  not have such information yet
    #     # df_unit = self.df_paradata[['interview__id', 'responsible']].copy()
    #     df_unit = self.df_paradata[['interview__id']].copy()
    #     df_unit.drop_duplicates(inplace=True)
    #     # df_unit.dropna(subset=['responsible'], inplace=True)
    #     df_unit.dropna(subset=['interview__id'], inplace=True)
    #     return df_unit

    @property
    def df_unit_score(self):
        for method_name in self.get_make_methods(method_type='score', level='unit'):
            feature_name = method_name.replace('make_score_unit', 'f')
            if feature_name in self._allowed_features and self._score_columns is None:
                try:
                    getattr(self, method_name)(feature_name)
                except Exception as e:
                    print("ERROR ON FEATURE SCORE: {}, It won't be used in further calculation".format(feature_name))
        self._score_columns = ['interview__id', 'responsible'] + [col for col in self._df_unit if 's__' in col]
        return self._df_unit[self._score_columns]

    def make_global_score(self):
        scaler = StandardScaler()
        df_unit_score = self.df_unit_score.copy()
        score_columns = [col for col in df_unit_score.columns if col.startswith('s__')]
        df = df_unit_score[score_columns].copy()
        df = pd.DataFrame(scaler.fit_transform(df), columns=score_columns)
        pca = PCA(n_components=0.99, whiten=True)

        # Conduct PCA
        df_pca = pca.fit_transform(df.fillna(0))
        scaler = MinMaxScaler(feature_range=(0, 100))
        self._df_unit['unit_risk_score'] = (df_pca * pca.explained_variance_ratio_).sum(axis=1)

        self._df_unit['unit_risk_score'] = 100 - scaler.fit_transform(self._df_unit[['unit_risk_score']])

    def save(self):
        # TODO reduce decimal points to first digit
        df = self._df_unit[['interview__id', 'responsible', 'unit_risk_score']].copy()
        df.sort_values('unit_risk_score', inplace=True)
        file_name = "_".join([self.config.surveys[0], self.config.survey_version[0], 'unit_risk_score']) + ".csv"
        output_path = os.path.join(self.config.data.results, file_name)
        df.to_csv(output_path, index=False)
        print(f'SUCCESS! you can find the unit_risk_score output file in {self.config.data.results}')

    def make_score_unit__numeric_response(self, feature_name):
        pass

    def make_score_unit__first_digit(self, feature_name):
        data = self.make_score__first_digit()
        data['total'] = data.drop(columns='responsible').sum(1)
        self._df_unit[feature_name.replace('f__', 's__')] = self._df_unit['responsible'].map(
            data.set_index('responsible')['total'])

    def make_score_unit__last_digit(self, feature_name):
        pass

    def make_score_unit__first_decimal(self, feature_name):
        data = self.make_score__first_decimal()
        selected_columns = [col for col in data.columns if feature_name.replace('f__', '__') in col]
        data['total'] = data[selected_columns].sum(1)
        data = data.groupby('interview__id')['total'].mean()
        data = data.reset_index()
        # data[['responsible','total']]
        self._df_unit[feature_name.replace('f__', 's__')] = self._df_unit['interview__id'].map(
            data.set_index('interview__id')['total'])

    def make_score_unit__answer_position(self, feature_name):
        data = self.make_score__answer_position()
        selected_columns = [col for col in data.columns if feature_name.replace('f__', '__') in col]
        data['total'] = data[selected_columns].mean(1)
        data = data.groupby('interview__id')['total'].mean()
        data = data.reset_index()
        self._df_unit[feature_name.replace('f__', 's__')] = self._df_unit['interview__id'].map(
            data.set_index('interview__id')['total'])

    def make_score_unit__answer_selected(self, feature_name):
        data = self.make_score__answer_selected()
        selected_columns = [col for col in data.columns if feature_name.replace('f__', '__') in col]
        data['total'] = data[selected_columns].mean(1)
        data = data.groupby('interview__id')['total'].mean()
        data = data.reset_index()
        self._df_unit[feature_name.replace('f__', 's__')] = self._df_unit['interview__id'].map(
            data.set_index('interview__id')['total'])

    def make_score_unit__single_question(self, feature_name):
        data = self.make_score__single_question()
        selected_columns = [col for col in data.columns if feature_name.replace('f__', '__') in col]
        data['total'] = data[selected_columns].mean(1)
        self._df_unit[feature_name.replace('f__', 's__')] = self._df_unit['responsible'].map(
            data.set_index('responsible')['total'])

    def make_score_unit__multi_option_question(self, feature_name):
        data = self.make_score__multi_option_question()
        selected_columns = [col for col in data.columns if feature_name.replace('f__', '__') in col]
        data['total'] = data[selected_columns].mean(1)
        self._df_unit[feature_name.replace('f__', 's__')] = self._df_unit['responsible'].map(
            data.set_index('responsible')['total'])

    def make_score_unit__answer_time_set(self, feature_name):
        data = self.make_score__answer_time_set()
        score_name = feature_name.replace('f__', 's__')
        # take the max number of anomaly for each question, i.e. 'roster_level' + 'variable_name'
        data['roster_variable'] = data['roster_level'].astype(str) + data['variable_name'].astype(str)

        data = data.groupby(['interview__id', 'roster_variable'])[score_name].max()
        data = data.reset_index()
        data = data.groupby('interview__id')[score_name].sum()

        self._df_unit[score_name] = self._df_unit['interview__id'].map(data)
        # Normalize by the total number of answer set
        self._df_unit[score_name] = self._df_unit[score_name] / self._df_unit['f__number_answered']
        # There might be some odd cases where the number of time set is greater than the number of answer sets,
        # this is due to some case where the variable "interviewing" is set to true but most of events happens
        # after it has been already opened by either supervisor or HQ
        self._df_unit[score_name] = self._df_unit[score_name].apply(lambda x: x if x <= 1 else 1)

    def make_score_unit__answer_removed(self, feature_name):
        data = self.make_score__answer_removed()
        score_name = feature_name.replace('f__', 's__')
        # take the max number of anomaly for each question, i.e. 'roster_level' + 'variable_name'
        data['roster_variable'] = data['roster_level'].astype(str) + data['variable_name'].astype(str)

        data = data.groupby(['interview__id', 'roster_variable'])[score_name].max()
        data = data.reset_index()
        data = data.groupby('interview__id')[score_name].sum()

        self._df_unit[score_name] = self._df_unit['interview__id'].map(data)
        # Normalize by the total number of answer set
        self._df_unit[score_name] = self._df_unit[score_name] / self._df_unit['f__number_answered']
        # There might be some odd cases where the number of time set is greater than the number of answer sets,
        # this is due to some case where the variable "interviewing" is set to true but most of events happens
        # after it has been already opened by either supervisor or HQ
        self._df_unit[score_name] = self._df_unit[score_name].apply(lambda x: x if x <= 1 else 1)

    def make_score_unit__answer_changed(self, feature_name):
        data = self.make_score__answer_changed()
        score_name = feature_name.replace('f__', 's__')
        # take the max number of anomaly for each question, i.e. 'roster_level' + 'variable_name'
        data['roster_variable'] = data['roster_level'].astype(str) + data['variable_name'].astype(str)

        data = data.groupby(['interview__id', 'roster_variable'])[score_name].max()
        data = data.reset_index()
        data = data.groupby('interview__id')[score_name].sum()

        self._df_unit[score_name] = self._df_unit['interview__id'].map(data)
        # Normalize by the total number of answer set
        self._df_unit[score_name] = self._df_unit[score_name] / self._df_unit['f__number_answered']
        # There might be some odd cases where the number of time set is greater than the number of answer sets,
        # this is due to some case where the variable "interviewing" is set to true but most of events happens
        # after it has been already opened by either supervisor or HQ
        self._df_unit[score_name] = self._df_unit[score_name].apply(lambda x: x if x <= 1 else 1)


    def make_score_unit__sequence_jump(self, feature_name):
        feature_name = 'f__sequence_jump'
        score_name = feature_name.replace('f__', 's__')
        data = self.make_score__sequence_jump()

        data[score_name] = data.drop(columns=['interview__id']).sum(1)

        self._df_unit[score_name] = self._df_unit['interview__id'].map(
            data.set_index('interview__id')[score_name]
        )

    def make_score_unit__answer_duration(self, feature_name):
        data = self.make_score__answer_duration()
        self._df_unit['s__answer_duration_lower_outliers'] = self._df_unit['interview__id'].map(
            data.set_index('interview__id')['s__answer_duration_lower_outliers']
        )
        self._df_unit['s__answer_duration__upper_outliers'] = self._df_unit['interview__id'].map(
            data.set_index('interview__id')['s__answer_duration__upper_outliers']
        )

    def make_score_unit__time_changed(self, feature_name):
        temp = (
            self.df_item[self.df_item[feature_name] < 0].groupby('interview__id')['responsible'].count()).reset_index()
        score_name = feature_name.replace('f__', 's__')
        self._df_unit[score_name] = self._df_unit['interview__id'].map(
            temp.set_index('interview__id')['responsible'])



    def make_score_unit__total_duration(self, feature_name):
        score_name = feature_name.replace('f__', 's__')
        self._df_unit[score_name] = self._df_unit[feature_name]

    def make_score_unit__total_elapse(self, feature_name):
        score_name = feature_name.replace('f__', 's__')
        self._df_unit[score_name] = self._df_unit[feature_name]

    def make_score_unit__pause_duration(self, feature_name):
        score_name = feature_name.replace('f__', 's__')
        self._df_unit[score_name] = self._df_unit[feature_name]

    def make_score_unit__pause_count(self, feature_name):
        score_name = feature_name.replace('f__', 's__')
        self._df_unit[score_name] = self._df_unit[feature_name]

    def make_score_unit__number_answered(self, feature_name):
        score_name = feature_name.replace('f__', 's__')
        self._df_unit[score_name] = self._df_unit[feature_name]

    def make_score_unit__number_unanswered(self, feature_name):
        score_name = feature_name.replace('f__', 's__')
        self._df_unit[score_name] = self._df_unit[feature_name]

    def make_score_unit__pause_duration(self, feature_name):
        score_name = feature_name.replace('f__', 's__')
        self._df_unit[score_name] = self._df_unit[feature_name]

    def make_score_unit__gps(self, feature_name):
        data = self.make_score__gps()
        features = ['s__proximity_counts', 's__spatial_outlier']

        data = data.groupby('interview__id')[features].sum()
        data = data.reset_index()

        self._df_unit['s__proximity_counts'] = self._df_unit['interview__id'].map(
            data.set_index('interview__id')['s__proximity_counts']
        )

        self._df_unit['s__spatial_outlier'] = self._df_unit['interview__id'].map(
            data.set_index('interview__id')['s__spatial_outlier']
        )

        data = self.df_item.groupby('interview__id')[feature_name].sum()
        data = data.reset_index()
        score_name = feature_name.replace('f__', 's__')
        self._df_unit[score_name] = self._df_unit['interview__id'].map(
            data.set_index('interview__id')[feature_name]
        )

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
