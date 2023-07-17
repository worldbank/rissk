import pandas as pd
from omegaconf import DictConfig
import hydra


####################################################
######### Set of funtions processing Paradata #######
####################################################


class DataProcessing:

    def __init__(self, paradata, microdata, questionaire, config):
        self._df_paradata = paradata
        self._df_microdata = microdata
        self._df_questionaire = questionaire
        self.config = config

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


class ParaDataProcessing(DataProcessing):

    def __init__(self, paradata, microdata, questionnaire, config, new_var):
        super().__init__(paradata, microdata, questionnaire, config)

        self.df_active_paradata = self.get_df_active_paradata()
        self._new_var = new_var

    group_columns = ['interview__id', 'param', 'roster_level']

    time_group_columns = ['interview__id', 'variable_name', 'roster_level']

    def get_df_active_paradata(self):
        # generate df with active events done by interviewer prior to rejection/review

        vars_needed = ['interview__id', 'order', 'event', 'responsible', 'role', 'tz_offset', 'param', 'answer',
                       'roster_level', 'datetime_utc', 'variable_name', 'question_seq', 'type', 'question_type',
                       'survey_name', 'survey_version']
        df_active = self._df_paradata[vars_needed].copy().sort_values(['interview__id', 'order']).reset_index()

        # only keep events done by interview (in most cases this should be all,
        # after above filters, just in case supervisor or HQ answered something while interviewer answered on web mode)
        df_active = df_active[df_active['role'] == 1]
        # TODO, remove hidden questions

        # streamline missing (empty, NaN) to '', important to identify duplicates in terms of roster below
        df_active.fillna('', inplace=True)

        # only keep interviewing events prior to Supervisor/HQ interaction
        events_split = ['RejectedBySupervisor', 'OpenedBySupervisor', 'OpenedByHQ', 'RejectedByHQ']
        grouped = df_active.groupby('interview__id')
        df_active['interviewing'] = False
        for _, group_df in grouped:
            matching_events = group_df['event'].isin(events_split)
            if matching_events.any():
                first_reject_index = matching_events.idxmax() - 1
                min_index = group_df.index.min()
                df_active.loc[min_index:first_reject_index, 'interviewing'] = True
        df_active = df_active[df_active['interviewing']]
        df_active = df_active.drop(columns=['interviewing'])

        # only keep active events
        events_to_keep = ['interview_created', 'AnswerSet', 'Resumed', 'AnswerRemoved', 'CommentSet', 'Restarted']
        df_active = df_active[df_active['event'].isin(events_to_keep)]
        return df_active.copy()


    def add_list_question(self):
        self._df_paradata['answer_changed'] = False

        df_para_list = self._df_paradata[
            (self._df_paradata['type'] == 'text_list_question') & (self._df_paradata['event'] == 'answer_set')].copy()
        grouped_list = df_para_list.groupby(self.group_columns)
        for _, group in grouped_list:
            prev_answers = set()  # set an empty set for previous answers
            for index, row in group.iterrows():
                row_answers = set(row['answer'].split('|')) if pd.notnull(row['answer']) else set()
                if prev_answers.difference(row_answers):
                    df_para_list.at[
                        index, 'answer_changed'] = True  # can be removed, just to verify more easily
                    self._df_paradata.at[index, 'answer_changed'] = True
                prev_answers = row_answers

    def add_single_answer_questions(self):
        df_para_question = self._df_paradata[
            (~self._df_paradata['type'].isin(
                ['yes_no_question', 'multy_options_question', 'text_list_question', 'variable'])) & (
                    self._df_paradata['event'] == 'answer_set')].copy()
        df_para_question = df_para_question[df_para_question.duplicated(subset=self.group_columns, keep=False)]
        if df_para_question.shape[0] > 0:
            grouped_question = df_para_question.groupby(self.group_columns)
            for _, group in grouped_question:
                prev_answer = None  # set an empty answer for previous answers
                for index, row in group.iterrows():
                    row_answer = row['answer']
                    if prev_answer is not None and prev_answer != row_answer:
                        df_para_question.at[
                            index, 'answer_changed'] = True  # can be removed, just to verify more easily
                        self._df_paradata.at[index, 'answer_changed'] = True
                    prev_answer = row_answer

    def add_yes_no_questions(self):
        df_para_yesno = self._df_paradata[
            (self._df_paradata['type'] == 'yes_no_question') & (self._df_paradata['event'] == 'answer_set')].copy()
        if df_para_yesno.shape[0] > 0:
            df_para_yesno[['yes_answers', 'no_answers']] = df_para_yesno['answer'].str.split('|', expand=True)
            grouped_yesno = df_para_yesno.groupby(self.group_columns)

            for _, group in grouped_yesno:
                prev_yes_answers = set()  # set an empty set for previous yes-answers
                for index, row in group.iterrows():
                    yes_answers = set(row['yes_answers'].split(', ')) if pd.notnull(row['yes_answers']) else set()
                    no_answers = set(row['no_answers'].split(', ')) if pd.notnull(row['no_answers']) else set()

                    if len(prev_yes_answers.intersection(no_answers)) > 0:
                        df_para_yesno.at[
                            index, 'answer_changed'] = True  # can be removed, just to verify more easily
                        self._df_paradata.at[index, 'answer_changed'] = True
                    prev_yes_answers = yes_answers

    def add_multi_answer_questions(self):
        df_para_multi = self._df_paradata[
            (self._df_paradata['type'] == 'multy_options_question') & (
                    self._df_paradata['event'] == 'answer_set')].copy()
        if df_para_multi.shape[0] > 0:
            grouped_multi = df_para_multi.groupby(self.group_columns)
            for _, group in grouped_multi:
                prev_answers = set()  # set an empty set for previous answers
                for index, row in group.iterrows():
                    row_answers = set(row['answer'].split(', ')) if pd.notnull(row['answer']) else set()
                    if prev_answers.difference(row_answers):
                        df_para_multi.at[
                            index, 'answer_changed'] = True  # can be removed, just to verify more easily
                        self._df_paradata.at[index, 'answer_changed'] = True
                    prev_answers = row_answers

    @staticmethod
    def filter_events(df_time):
        # only keep  interviewing events prior to Supervisor/HQ interaction
        events_split = ['rejected_by_supervisor', 'opened_by_supervisor', 'opened_by_hq', 'rejected_by_hq']
        grouped = df_time.groupby('interview__id')
        df_time['interviewing'] = False
        for _, group_df in grouped:
            first_reject_index = group_df['event'].isin(events_split).idxmax() - 1
            min_index = group_df.index.min()
            df_time.loc[min_index:first_reject_index, 'interviewing'] = True
        df_time = df_time[df_time['interviewing']].copy()
        df_time = df_time.drop(columns=['interviewing'])
        return df_time

    def make_df_time(self):
        # generate new df
        vars_needed = ['interview__id', 'order', 'event', 'responsible', 'role', 'tz_offset', 'param', 'answer',
                       'roster_level', 'datetime_utc', 'variable_name', 'question_seq', 'type', 'question_type']
        df_time = self._df_paradata[vars_needed].copy()

        # streamline missing (empty, NaN) to '', important to identify duplicates in terms of roster below
        df_time.fillna('', inplace=True)

        # keep only events relevant for calculating response latency
        df_time = self.filter_events(df_time)

        # events_to_drop = ['SupervisorAssigned', 'InterviewerAssigned',
        # 'KeyAssigned', 'VariableDisabled','ReceivedByInterviewer',
        # 'KeyAssigned', 'VariableEnabled', 'VariableSet',
        # 'QuestionDeclaredInvalid', 'QuestionDeclaredValid',
        # 'Completed', 'TranslationSwitched',
        # 'ReceivedBySupervisor','opened_by_supervisor',
        # 'ApproveBySupervisor','ClosedBySupervisor',
        # 'InterviewModeChanged', 'Paused', 'rejected_by_supervisor']

        events_to_keep = ['interview_created', 'answer_set', 'resumed', 'answer_removed', 'comment_set',
                          'restarted']  # check in other example data sets that there are no other relevant events
        df_time = df_time[df_time['event'].isin(events_to_keep)]

        # keep only events done by interview
        # (should not exist for most cases after above filters,
        # just in case supervisor or HQ answered something while interviewer answered on web mode)
        df_time = df_time[df_time['role'] == 1]

        # if the same question was repeatedly answered/commented on the same roster level,
        # keep only the last one (to take the overall time for the question)

        df_time['is_diff'] = (df_time[self.time_group_columns].shift() != df_time[self.time_group_columns]).any(axis=1)
        df_time['keep'] = df_time['is_diff'].shift(-1, fill_value=True)
        df_time = df_time[df_time['keep']]
        df_time.drop(columns=['is_diff', 'keep'], inplace=True)

        # calculate time difference in seconds
        df_time['time_difference'] = df_time.groupby('interview__id')['datetime_utc'].diff()
        df_time['time_difference'] = df_time['time_difference'].dt.total_seconds()

        # keep only answer_set and comment_set events, we ignore timing for answer_removed as it is also system generated
        df_time = df_time[df_time['event'].isin(['answer_set', 'comment_set'])].copy()
        return df_time

    def make_df_latency(self, df_time):
        df_latency = df_time.groupby(self.time_group_columns).agg(
            total_duration=('time_difference', 'sum'),
            n_revisited=('time_difference', 'count')
        ).reset_index()

        return df_latency


class FeatureDataProcessing(DataProcessing):
    item_level_columns = ['interview__id', 'variable_name', 'roster_level']

    def make_feature_df(self):
        feat_item = self._df_microdata[
            self.item_level_columns + ['value', 'type', 'is_integer', 'n_answers', 'answer_sequence']].copy()

        feat_item['value'].fillna('', inplace=True)
        return feat_item
####################################################
######### Set of functions processing Paradata #######
####################################################
