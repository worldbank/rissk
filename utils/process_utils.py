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
        self._df_microdata = self.make_merging_column(microdata)
        self._df_questionaire = questionaire

        self._df_para_active = self.make_df_active_paradata()
        self._df_time_temp = self.make_df_time()
        self._df_last_temp = self.make_df_last()
        self.config = config

    def make_merging_column(self, df):
        # define internal variable for level columns
        df['merging_column'] = df[self.item_level_columns].apply(
            lambda row: '_'.join([str(row[col]) for col in self.item_level_columns]), axis=1)
        return df.copy()

    def make_df_time(self):
        # f__duration_answer, total time spent to record answers, i.e. sum of all time-intervals from active events ending with the item being AnswerSet or AnswerRemoved
        # f__duration_comment, total time spent to comment, i.e. sum of all time-intervals from active events ending with the item being CommentSet

        df_time = self._df_para_active.copy()

        # calculate time difference in seconds
        df_time['time_difference'] = df_time.groupby('interview__id')['datetime_utc'].diff()
        df_time['time_difference'] = df_time['time_difference'].dt.total_seconds()

        # time for answers/comments
        df_time['f__duration_answer'] = df_time.loc[
            df_time['event'].isin(['AnswerSet', 'AnswerRemoved']), 'time_difference']
        df_time['f__duration_comment'] = df_time.loc[df_time['event'] == 'CommentSet', 'time_difference']

        # summarize on item level
        df_time = df_time.groupby(self.item_level_columns+['merging_column']).agg(
            f__duration_answer=('f__duration_answer', 'sum'),
            f__duration_comment=('f__duration_comment', 'sum')
        ).reset_index()
        # TODO! WHY we drop rows without variable_name AFTER aggregation??
        # drop rows without VariableName
        df_time = df_time[df_time['variable_name'] != ''].copy()
        return df_time

    def make_df_active_paradata(self):
        self.process_paradata()
        # df_para_active, active events, prior rejection/review events, for questions with scope interviewer

        active_events = ['InterviewCreated', 'AnswerSet', 'Resumed', 'AnswerRemoved', 'CommentSet', 'Restarted']
        # only keep events done by interview (in most cases this should be all, after above filters,
        # just in case supervisor or HQ answered something while interviewer answered on web mode)
        # keep active events, prior rejection/review events, for questions with scope interviewer
        active_mask = (self._df_paradata['event'].isin(active_events)) & \
                      (self._df_paradata['interviewing']) & \
                      (self._df_paradata['question_scope'] == 0) & \
                      (self._df_paradata['role'] == 1)

        vars_needed = ['interview__id', 'order', 'event', 'responsible', 'role', 'tz_offset', 'param', 'answer',
                       'roster_level', 'datetime_utc', 'variable_name', 'question_sequence', 'question_scope', 'type',
                       'question_type', 'survey_name', 'survey_version', 'interviewing', 'merging_column']

        df_para_active = self._df_paradata.loc[active_mask, vars_needed].copy().sort_values(
            ['interview__id', 'order']).reset_index()

        return df_para_active.copy()

    def make_df_last(self):
        df_last = self._df_para_active[self._df_para_active['event'] == 'AnswerSet'].groupby('merging_column').last()
        df_last = df_last.sort_values(['interview__id', 'order']).reset_index()

        # f__previous_question, f__previous_answer, f__previous_roster for previous answer set
        df_last['f__previous_question'] = df_last.groupby('interview__id')['variable_name'].shift(
            fill_value='')
        df_last['f__previous_answer'] = df_last.groupby('interview__id')['answer'].shift(
            fill_value='')
        df_last['f__previous_roster'] = df_last.groupby('interview__id')['roster_level'].shift(
            fill_value='')
        df_last['f__answer_time_set'] = df_last['datetime_utc'].dt.hour + df_last[
            'datetime_utc'].dt.round(
            '30min').dt.minute
        # f__sequence_jump, Difference between actual answer sequence and
        # question sequence in the questionnaire, in difference to previous question
        df_last['answer_sequence'] = df_last.groupby('interview__id').cumcount() + 1
        df_last['diff'] = df_last['question_sequence'] - df_last['answer_sequence']
        df_last['f__sequence_jump'] = df_last['diff'].diff()

        return df_last

    def process_paradata(self):
        # dfs_paradata modifications, move to import-utils?

        # streamline missing (empty, NaN) to '', important to identify duplicates in terms of roster below
        self._df_paradata.fillna('', inplace=True)

        # interviewing, True prior to Supervisor/HQ interaction, else False
        events_split = ['RejectedBySupervisor', 'OpenedBySupervisor', 'OpenedByHQ', 'RejectedByHQ']
        grouped = self._df_paradata.groupby('interview__id')
        self._df_paradata['interviewing'] = False
        for _, group_df in grouped:
            matching_events = group_df['event'].isin(events_split)
            if matching_events.any():
                first_reject_index = matching_events.idxmax() - 1
                min_index = group_df.index.min()
                self._df_paradata.loc[min_index:first_reject_index, 'interviewing'] = True

    @property
    def get_df_paradata(self):
        return self._df_paradata

    @property
    def get_df_microdata(self):
        return self._df_microdata

    @property
    def get_df_questionaire(self):
        return self._df_questionaire

    def save_data(self, df, file_name):
        # TODO write generic method to save the data,
        pass


class FeatureDataProcessing(DataProcessing):

    def __init__(self, paradata, microdata, questionnaire, config):
        super().__init__(paradata, microdata, questionnaire, config)
        self._df_features = self.make_df_features()
        # define filter conditions
        self.text_question_mask = (self._df_features['type'] == 'TextQuestion')
        self.numeric_question_mask = (self._df_features['type'] == 'NumericQuestion') & (
                self._df_features['value'] != '')
        self.decimal_question_mask = (self._df_features['is_integer'] == False) & (self._df_features['value'] != '')
        self._applied_methods = []

    @property
    def df_features(self):
        for method_name in self.get_make_feature_methods():
            if method_name not in self._applied_methods:
                self._applied_methods.append(method_name)
                try:
                    getattr(self, method_name)()
                except:
                    print('ERROR ON ', method_name)
        return self._df_features

    def make_df_features(self):
        df_features = self._df_microdata[['value', 'type', 'is_integer',
                                          'n_answers', 'answer_sequence', 'merging_column']].copy()
        df_features['value'].fillna('', inplace=True)
        return df_features

    def make_feature__string_length(self):
        # f__string_length, length of string answer, if TextQuestions, empty if not
        self._df_features['f__string_length'] = pd.NA
        self._df_features.loc[self.text_question_mask, 'f__string_length'] = self._df_features.loc[
            self.text_question_mask, 'value'].str.len()
        self._df_features['f__string_length'] = self._df_features['f__string_length'].astype('Int64')

    def make_feature__numeric_response(self):
        # f__numeric_response, response, if NumericQuestions, empty if not
        self._df_features['f__numeric_response'] = np.nan
        self._df_features.loc[self.numeric_question_mask, 'f__numeric_response'] = \
            self._df_features[self.numeric_question_mask]['value'].astype(
                float)

    def make_feature__first_digit(self):
        # f__first_digit, first digit of the response if numeric question, empty if not
        self._df_features['f__first_digit'] = pd.NA
        self._df_features.loc[self.numeric_question_mask, 'f__first_digit'] = \
            self._df_features.loc[self.numeric_question_mask, 'value'].astype(str).str[0].astype('Int64')

    def make_feature__last_digit(self):
        # f__last_digit, modulus of 10 of the response if numeric question, empty if not
        self._df_features['f__last_digit'] = pd.NA
        self._df_features.loc[self.numeric_question_mask, 'f__last_digit'] = pd.to_numeric(
            self._df_features.loc[self.numeric_question_mask, 'value']).astype('int64') % 10

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
        self._df_features.loc[single_question_mask, 'f__answer_position'] = self._df_features.loc[single_question_mask].apply(
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

    def make_feature__duration_answer(self):
        self._df_features['f__duration_answer'] = self._df_features['merging_column'].map(
            self._df_time_temp.set_index('merging_column')['f__duration_answer'])

    def make_feature__duration_comment(self):
        self._df_features['f__duration_comment'] = self._df_features['merging_column'].map(
            self._df_time_temp.set_index('merging_column')['f__duration_comment'])

    def make_feature__previous_question(self):
        self._df_features['f__previous_question'] = self._df_features['merging_column'].map(
            self._df_last_temp.set_index('merging_column')['f__previous_question'])

    def make_feature__previous_answer(self):
        self._df_features['f__previous_answer'] = self._df_features['merging_column'].map(
            self._df_last_temp.set_index('merging_column')['f__previous_answer'])

    def make_feature__previous_roster(self):
        self._df_features['f__previous_roster'] = self._df_features['merging_column'].map(
            self._df_last_temp.set_index('merging_column')['f__previous_roster'])

    def make_feature__sequence_jump(self):
        self._df_features['f__sequence_jump'] = self._df_features['merging_column'].map(
            self._df_last_temp.set_index('merging_column')['f__sequence_jump'])

    def make_feature__answer_time_set(self):
        self._df_features['f__answer_time_set'] = self._df_features['merging_column'].map(
            self._df_last_temp.set_index('merging_column')['f__answer_time_set'])

    def get_make_feature_methods(self):
        return [method for method in dir(self) if method.startswith("make_feature__")
                and callable(getattr(self, method))]


class UnitDataProcessing(DataProcessing):

    def __init__(self, paradata, microdata, questionnaire, config):
        super().__init__(paradata, microdata, questionnaire, config)
        self._df_unit = self.make_df_unit()


    @property
    def df_features(self):
        for method_name in self.get_make_feature_methods():
            if method_name not in self._applied_methods:
                self._applied_methods.append(method_name)
                try:
                    getattr(self, method_name)()
                except:
                    print('ERROR ON ', method_name)
        return self._df_features

    def make_df_unit(self):
        df_features = self._df_microdata[['value', 'type', 'is_integer',
                                          'n_answers', 'answer_sequence', 'merging_column']].copy()
        df_features['value'].fillna('', inplace=True)
        return df_features