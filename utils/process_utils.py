import pandas as pd
from omegaconf import DictConfig
import hydra
import numpy as np


####################################################
######### Set of funtions processing #######
####################################################


class DataProcessing:

    def __init__(self, paradata, microdata, questionaire, config):
        self.item_level_columns = ['interview__id', 'variable_name', 'roster_level']
        self._df_paradata = self.make_merging_column(paradata)
        self.process_paradata()
        self._df_microdata = self.make_merging_column(microdata)
        self._df_questionaire = questionaire

        self._df_para_active = None
        self._df_time = None
        self._df_last = None
        self.config = config

    def make_merging_column(self, df):
        # define internal variable for level columns
        df['merging_column'] = df[self.item_level_columns].apply(
            lambda row: '_'.join([str(row[col]) for col in self.item_level_columns]), axis=1)
        return df.copy()

    @property
    def df_time(self):
        if self._df_time is None:
            # f__duration_answer, total time spent to record answers, i.e. sum of all time-intervals from active events ending with the item being AnswerSet or AnswerRemoved
            # f__duration_comment, total time spent to comment, i.e. sum of all time-intervals from active events ending with the item being CommentSet

            df_time = self.df_active_paradata.copy()

            # calculate time difference in seconds
            df_time['time_difference'] = df_time.groupby('interview__id')['datetime_utc'].diff()
            df_time['time_difference'] = df_time['time_difference'].dt.total_seconds()
            df_time['f__time_changed'] = np.where(df_time['time_difference'] < -180, df_time['time_difference'], np.nan)
            df_time.loc[df_time['time_difference'] < 0, 'time_difference'] = pd.NA
            # time for answers/comments
            df_time['f__duration_answer'] = df_time.loc[
                df_time['event'].isin(['AnswerSet', 'AnswerRemoved']), 'time_difference']
            df_time['f__duration_comment'] = df_time.loc[df_time['event'] == 'CommentSet', 'time_difference']

            # summarize on item level
            df_time = df_time.groupby(self.item_level_columns + ['merging_column']).agg(
                f__duration_answer=('f__duration_answer', 'sum'),
                f__duration_comment=('f__duration_comment', 'sum'),
                f__time_changed=('f__time_changed', 'sum')
            ).reset_index()

            self._df_time = df_time[df_time['variable_name'] != ''].copy()
        return self._df_time

    @property
    def df_active_paradata(self):
        if self._df_para_active is None:
            # df_para_active, active events, prior rejection/review events, for questions with scope interviewer

            active_events = ['InterviewCreated', 'AnswerSet', 'Resumed', 'AnswerRemoved', 'CommentSet', 'Restarted']
            # only keep events done by interview (in most cases this should be all, after above filters,
            # just in case supervisor or HQ answered something while interviewer answered on web mode)
            # keep active events, prior rejection/review events, for questions with scope interviewer
            active_mask = (self.df_paradata['event'].isin(active_events)) & \
                          (self.df_paradata['interviewing'] == True) & \
                          (self.df_paradata['question_scope'] == 0) & \
                          (self.df_paradata['role'] == 1)

            vars_needed = ['interview__id', 'order', 'event', 'responsible', 'role', 'tz_offset', 'param', 'answer',
                           'roster_level', 'datetime_utc', 'variable_name', 'question_sequence', 'question_scope',
                           'type',
                           'question_type', 'survey_name', 'survey_version', 'interviewing', 'merging_column',
                           'f__answer_year_set', 'f__answer_month_set',
                           'f__answer_day_set', 'f__half_hour', 'f__answer_time_set'
                           ]

            df_para_active = self.df_paradata.loc[active_mask, vars_needed].copy().sort_values(
                ['interview__id', 'order']).reset_index()
            self._df_para_active = df_para_active.copy()

        return self._df_para_active

    @property
    def df_last(self):
        if self._df_last is None:
            df_last = self.df_active_paradata[self.df_active_paradata['event'] == 'AnswerSet'].groupby(
                'merging_column').last()
            df_last = df_last.sort_values(['interview__id', 'order']).reset_index()

            # f__previous_question, f__previous_answer, f__previous_roster for previous answer set
            df_last['f__previous_question'] = df_last.groupby('interview__id')['variable_name'].shift(
                fill_value='')
            df_last['f__previous_answer'] = df_last.groupby('interview__id')['answer'].shift(
                fill_value='')
            df_last['f__previous_roster'] = df_last.groupby('interview__id')['roster_level'].shift(
                fill_value='')


            # f__in_working_hours, indication if f__half_hour is within working hours
            half_hour_counts = df_last['f__half_hour'].value_counts().sort_index()

            threshold = half_hour_counts.median() * 0.33  # approach 1: interval < 1/3 of the median count of answers set
            working_hours_1 = half_hour_counts[half_hour_counts >= threshold].index.tolist()

            cumulative_share = (half_hour_counts.sort_values().cumsum() / half_hour_counts.sum()).sort_index()
            working_hours_2 = half_hour_counts[
                cumulative_share >= 0.05].index.tolist()  # approach 2: the least frequent intervals with total of 5% of answers set

            df_last['f__in_working_hours'] = df_last['f__half_hour'].isin(working_hours_2)

            # f__sequence_jump, Difference between actual answer sequence and
            # question sequence in the questionnaire, in difference to previous question
            df_last['answer_sequence'] = df_last.groupby('interview__id').cumcount() + 1
            df_last['diff'] = df_last['question_sequence'] - df_last['answer_sequence']
            df_last['f__sequence_jump'] = df_last.groupby('interview__id')['diff'].diff()
            self._df_last = df_last.copy()
        return self._df_last

    def process_paradata(self):

        # streamline missing (empty, NaN) to '', important to identify duplicates in terms of roster below
        self._df_paradata.fillna('', inplace=True)

        self._df_paradata['f__answer_time_set'] = (self._df_paradata['datetime_utc'].dt.hour + self._df_paradata[
            'datetime_utc'].dt.round(
            '30min').dt.minute / 60)
        # f__half_hour, half-hour interval of last time answered
        self._df_paradata['f__half_hour'] = (self._df_paradata['datetime_utc'].dt.hour + (self._df_paradata['datetime_utc'].dt.round(
            '30min').dt.minute) / 100)

        self._df_paradata['f__answer_day_set'] = self._df_paradata['datetime_utc'].dt.day
        self._df_paradata['f__answer_month_set'] = self._df_paradata['datetime_utc'].dt.month
        self._df_paradata['f__answer_year_set'] = self._df_paradata['datetime_utc'].dt.year

        # interviewing, True prior to Supervisor/HQ interaction, else False
        events_split = ['RejectedBySupervisor', 'OpenedBySupervisor', 'OpenedByHQ', 'RejectedByHQ']
        grouped = self._df_paradata.groupby('interview__id')
        self._df_paradata['interviewing'] = True
        for _, group_df in grouped:
            matching_events = group_df['event'].isin(events_split)
            if matching_events.any():
                match_index = matching_events.idxmax()
                max_index = group_df.index.max()
                self._df_paradata.loc[match_index:max_index, 'interviewing'] = False


    @property
    def df_paradata(self):
        return self._df_paradata

    @property
    def df_microdata(self):
        return self._df_microdata

    @property
    def df_questionaire(self):
        return self._df_questionaire

    def save_data(self, df, file_name):
        # TODO write generic method to save the data,
        pass

    def get_make_methods(self, method_type='feature'):
        return [method for method in dir(self) if method.startswith(f"make_{method_type}__")
                and callable(getattr(self, method))]


class FeatureDataProcessing(DataProcessing):

    def __init__(self, paradata, microdata, questionnaire, config):
        super().__init__(paradata, microdata, questionnaire, config)
        self._df_features = self.make_df_features()
        # define filter conditions
        self.text_question_mask = (self._df_features['type'] == 'TextQuestion')
        self.numeric_question_mask = (self._df_features['type'] == 'NumericQuestion') & \
                                     (self._df_features['value'] != '') & \
                                     (~pd.isnull(self._df_features['value']) &
                                      (self._df_features['value'] != -999999999))
        self.decimal_question_mask = (self._df_features['is_integer'] == False) & (self._df_features['value'] != '')
        self._applied_methods = []

    @property
    def df_features(self):
        for method_name in self.get_make_methods():
            if method_name not in self._applied_methods:
                self._applied_methods.append(method_name)
                try:
                    getattr(self, method_name)()
                except:
                    print('ERROR ON ', method_name)
        return self._df_features

    def make_df_features(self):
        df_features = self._df_microdata[['value', 'type', 'is_integer', 'qnr_seq',
                                          'n_answers', 'answer_sequence',
                                          'merging_column'] + self.item_level_columns].copy()
        # df_features['value'].fillna('', inplace=True)
        paradata_columns = ['responsible', 'f__answer_year_set', 'f__answer_month_set',
                            'f__answer_day_set', 'f__half_hour', 'f__answer_time_set']
        df_features = df_features.merge(self.df_active_paradata[paradata_columns+['merging_column']], how='left', on='merging_column')

        return df_features.copy()

    def make_feature__string_length(self):
        # f__string_length, length of string answer, if TextQuestions, empty if not
        self._df_features['f__string_length'] = pd.NA
        self._df_features.loc[self.text_question_mask, 'f__string_length'] = self._df_features.loc[
            self.text_question_mask, 'value'].str.len().astype('Int64')

    def make_feature__numeric_response(self):
        # f__numeric_response, response, if NumericQuestions, empty if not
        self._df_features['f__numeric_response'] = np.nan
        self._df_features.loc[self.numeric_question_mask, 'f__numeric_response'] = \
            self._df_features[self.numeric_question_mask]['value'].astype(
                float)

    # def make_feature__first_digit(self):
    #     # f__first_digit, first digit of the response if numeric question, empty if not
    #     self._df_features['f__first_digit'] = pd.NA
    #     self._df_features.loc[self.numeric_question_mask, 'f__first_digit'] = \
    #         self._df_features.loc[self.numeric_question_mask, 'value'].fillna('').astype(str).str[0].astype('Int64')

    def make_feature__last_digit(self):
        # f__last_digit, modulus of 10 of the response if numeric question, empty if not
        self._df_features['f__last_digit'] = pd.NA
        self._df_features.loc[self.numeric_question_mask, 'f__last_digit'] = pd.to_numeric(
            self._df_features.loc[self.numeric_question_mask, 'value'].fillna('')).astype('int64') % 10

    def make_feature__first_decimal(self):
        # f__first_decimal, first decimal digit if numeric question, empty if not
        self._df_features['f__first_decimal'] = pd.NA
        values = self._df_features.loc[self.decimal_question_mask, 'value'].astype(float)
        self._df_features.loc[self.decimal_question_mask, 'f__first_decimal'] = np.floor(values * 10) % 10
        self._df_features['f__first_decimal'] = self._df_features['f__first_decimal'].astype('Int64')

    def make_feature__answer_position(self):
        # f__rel_answer_position, relative position of the selected answer
        self._df_features['f__answer_position'] = pd.NA
        single_question_mask = (self._df_features['type'] == 'SingleQuestion') & (
                self._df_features['n_answers'] > 2)  # only questions with more than two answers
        self._df_features.loc[single_question_mask, 'f__answer_position'] = self._df_features.loc[
            single_question_mask].apply(
            lambda row: round(row['answer_sequence'].index(row['value']) / (row['n_answers'] - 1), 3) if (row[
                                                                                                              'value'] in
                                                                                                          row[
                                                                                                              'answer_sequence']) and pd.notnull(
                row['value']) else None, axis=1)

    def make_feature__gps(self):
        # f__Latitude, f__Longitude, f__Accuracy
        gps_mask = self._df_features['type'] == 'GpsCoordinateQuestion'
        gps_df = self._df_features.loc[gps_mask, 'value'].str.split(',', expand=True)
        gps_df.columns = ['gps__Latitude', 'gps__Longitude', 'gps__Accuracy', 'gps__Altitude', 'gps__Timestamp']
        self._df_features.loc[gps_mask, 'f__Latitude'] = pd.to_numeric(gps_df['gps__Latitude'], errors='coerce')
        self._df_features.loc[gps_mask, 'f__Longitude'] = pd.to_numeric(gps_df['gps__Longitude'], errors='coerce')
        self._df_features.loc[gps_mask, 'f__Accuracy'] = pd.to_numeric(gps_df['gps__Accuracy'], errors='coerce')
        self._df_features.drop([col for col in self._df_features.columns if col.startswith('gps__')], axis=1,
                               inplace=True)

    def make_feature__answers_share_selected(self):
        # f__answers_selected, number of answers selected in a multi-answer or list question
        # f__share_selected, share between answers selected, and available answers (only for unlinked questions)
        def count_elements_or_nan(val):  # Function to calculate number of elements in a list or return nan
            if isinstance(val, list):
                return len(val)
            else:
                return np.nan

        multi_list_mask = self._df_features['type'].isin(['MultyOptionsQuestion', 'TextListQuestion'])
        self._df_features.loc[multi_list_mask, 'f__answers_selected'] = self._df_features.loc[
            multi_list_mask, 'value'].apply(
            count_elements_or_nan)
        self._df_features['f__share_selected'] = round(
            self._df_features['f__answers_selected'] / self._df_features['n_answers'], 3)

    def make_feature__answer_duration(self):
        # merge into feat_item
        # TODO! WHY do we do an outer join?? Shouldn't we just take those answers that are in microdata??

        # self.merged_temp = self._df_features.merge(self._df_time_temp, on='merging_column', how='outer',
        #                                            indicator=True)
        # self._df_features = self.merged_temp.copy()
        pass

    def make_feature__time_changed(self):
        self._df_features['f__time_changed'] = self._df_features['merging_column'].map(
            self.df_time.set_index('merging_column')['f__time_changed'])

    def make_feature__duration_answer(self):
        self._df_features['f__duration_answer'] = self._df_features['merging_column'].map(
            self.df_time.set_index('merging_column')['f__duration_answer'])

    def make_feature__duration_comment(self):
        self._df_features['f__duration_comment'] = self._df_features['merging_column'].map(
            self.df_time.set_index('merging_column')['f__duration_comment'])

    def make_feature__previous_question(self):
        self._df_features['f__previous_question'] = self._df_features['merging_column'].map(
            self.df_last.set_index('merging_column')['f__previous_question'])

    def make_feature__previous_answer(self):
        self._df_features['f__previous_answer'] = self._df_features['merging_column'].map(
            self.df_last.set_index('merging_column')['f__previous_answer'])

    def make_feature__previous_roster(self):
        self._df_features['f__previous_roster'] = self._df_features['merging_column'].map(
            self.df_last.set_index('merging_column')['f__previous_roster'])

    def make_feature__sequence_jump(self):
        self._df_features['f__sequence_jump'] = self._df_features['merging_column'].map(
            self.df_last.set_index('merging_column')['f__sequence_jump'])

    def make_feature__answer_time_set(self):
        self._df_features['f__answer_time_set'] = self._df_features['merging_column'].map(
            self.df_last.set_index('merging_column')['f__half_hour'])


class UnitDataProcessing(DataProcessing):

    def __init__(self, paradata, microdata, questionnaire, config):
        super().__init__(paradata, microdata, questionnaire, config)
        self._df_changes = None
        self._df_unit = self.make_df_unit()

    @property
    def df_unit(self):
        for method_name in self.get_make_methods():
            if method_name not in self._applied_methods:
                self._applied_methods.append(method_name)
                try:
                    getattr(self, method_name)()
                except:
                    print('ERROR ON ', method_name)
        return self._df_features

    @property
    def df_changed(self):
        if self._df_changes is None:
            df_changed_temp = self.df_active_paradata[self.df_active_paradata['event'] == 'AnswerSet'].copy()
            df_changed_temp['f__answer_changed'] = False

            # list and multi-select questions (without yes_no_mode)
            list_mask = (df_changed_temp['type'] == 'TextListQuestion')
            multi_mask = (df_changed_temp['yes_no_view'] == False)
            df_changed_temp['answer_list'] = pd.NA
            df_changed_temp.loc[list_mask, 'answer_list'] = df_changed_temp.loc[list_mask, 'answer'].str.split('|')
            df_changed_temp.loc[multi_mask, 'answer_list'] = df_changed_temp.loc[multi_mask, 'answer'].str.split(
                ', |\\|')
            df_changed_temp['prev_answer_list'] = df_changed_temp.groupby(self.item_level_columns)[
                'answer_list'].shift()
            answers_mask = df_changed_temp['prev_answer_list'].notna()
            df_changed_temp.loc[answers_mask, 'f__answer_changed'] = df_changed_temp.loc[answers_mask].apply(
                lambda row: not set(row['prev_answer_list']).issubset(set(row['answer_list'])), axis=1)

            # single answer question
            df_changed_temp['prev_answer'] = df_changed_temp.groupby(self.item_level_columns)['answer'].shift()
            single_answer_mask = (~df_changed_temp['type'].isin(['MultyOptionsQuestion', 'TextListQuestion'])) & \
                                 (df_changed_temp['prev_answer'].notna()) & \
                                 (df_changed_temp['answer'] != df_changed_temp['prev_answer'])
            df_changed_temp.loc[single_answer_mask, 'f__answer_changed'] = True

            # yes_no_view questions
            yesno_mask = (df_changed_temp['yes_no_view'] == True)
            df_filtered = df_changed_temp[yesno_mask].copy()
            df_filtered[['yes_list', 'no_list']] = df_filtered['answer'].str.split('|', expand=True)
            df_filtered['yes_list'] = df_filtered['yes_list'].str.split(', ').apply(
                lambda x: [] if x == [''] or x is None else x)
            df_filtered['no_list'] = df_filtered['no_list'].str.split(', ').apply(
                lambda x: [] if x == [''] or x is None else x)
            df_filtered['prev_yes_list'] = df_filtered.groupby(self.item_level_columns)['yes_list'].shift(fill_value=[])
            df_filtered['prev_no_list'] = df_filtered.groupby(self.item_level_columns)['no_list'].shift(fill_value=[])
            df_changed_temp.loc[yesno_mask, 'f__answer_changed'] = df_filtered.apply(
                lambda row: not set(row['prev_yes_list']).issubset(set(row['yes_list'])), axis=1)
            df_changed_temp.loc[yesno_mask, 'f__answer_changed'] = df_filtered.apply(
                lambda row: not set(row['prev_no_list']).issubset(set(row['no_list'])), axis=1)

            # count on item level
            df_changed_temp = df_changed_temp.groupby(self.item_level_columns)['f__answer_changed'].sum().reset_index()
            self._df_changes = df_changed_temp.copy()
        return self._df_changes

    def make_feature__item_removed(self):
        if 'f__answer_removed' not in self.df_unit.columns:
            # f__answer_removed, answers removed (by interviewer, or by system as a result of interviewer action).
            removed_mask = (self.df_paradata['interviewing']) & \
                           (self.df_paradata['interviewing'] == True) & \
                           (self.df_paradata['event'] == 'AnswerRemoved')
            df_item_removed = self.df_paradata[removed_mask]

            df_item_removed = df_item_removed.groupby(self.item_level_columns).agg(
                f__answer_removed=('order', 'count'),
            ).reset_index()
            # to be merged into df_item

            df_unit_removed = df_item_removed.groupby('interview__id').agg(
                f__answer_removed=('f__answer_removed', 'sum'),
            )
            self.df_unit['f__answer_removed'] = self.df_unit['interview__id'].map(
                df_item_removed.set_index('interview__id')['f__answer_removed']
            )

    def make_feature__comments(self):

        if 'f__comments_set' not in self.df_unit or 'f__comment_length' not in self.df_unit:
            # f__comments_set, f_comment_length
            comment_mask = (self.df_paradata['event'] == 'CommentSet') & \
                           (self.df_paradata['role'] == 1) & \
                           (self.df_paradata['interviewing'])
            df_item_comment = self.df_paradata[comment_mask].copy()
            df_item_comment['f__comment_length'] = df_item_comment['answer'].str.len()
            df_item_comment = df_item_comment.groupby(self.item_level_columns).agg(
                f__comments_set=('order', 'count'),
                f__comment_length=('f__comment_length', 'sum'),
            ).reset_index()
            # to be merged into df_item

            df_unit_comment = df_item_comment.groupby('interview__id').agg(
                f__comments_set=('f__comments_set', 'sum'),
                f__comment_length=('f__comment_length', 'sum')
            ).reset_index()

            self.df_unit['f__comments_set'] = self.df_unit['interview__id'].map(
                df_unit_comment.set_index('interview__id')['f__comments_set']
            )

            self.df_unit['f__comment_length'] = self.df_unit['interview__id'].map(
                df_unit_comment.set_index('interview__id')['f__comment_length']
            )


    def make_feature__number_answers(self):
        answer_per_interview_df = self.df_active_paradata.groupby('interview__id').variable_name.nunique()
        answer_per_interview_df = answer_per_interview_df.reset_index()
        total_questions = self.df_questionaire[self.df_questionaire['type'].str.contains('Question')]['type'].count()
        self._df_unit['f__number_answers'] = self._df_features['interview__id'].map(
            answer_per_interview_df.set_index('interview__id')['variable_name']/total_questions)


    def make_df_unit(self):
        df_unit = pd.DataFrame(self.df_paradata.interview__id.unique(), columns=['interview__id'])
        return df_unit
