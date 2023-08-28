from src.import_manager import *


class FeatureProcessing(ImportManager):

    def __init__(self, config):
        super().__init__(config)

        self.extract()
        paradata, questionaire, microdata = self.get_dataframes(reload=self.config['reload'],
                                                                save_to_disk=self.config['save_to_disk'])
        print('Data Loaded')
        self._allowed_features = ['f__' + k for k, v in config['features'].items() if v['use']]
        self.item_level_columns = ['interview__id', 'variable_name', 'roster_level']
        self._df_paradata = self.process_paradata(paradata)
        print('Paradata Processed')
        self._df_item = self.make_df_item(microdata)
        print('Items Build')
        self._df_unit = self.make_df_unit()
        print('Unit Build')
        # Define ask that get recurrently used
        self.numeric_question_mask = (
                (self._df_item['type'] == 'NumericQuestion') &
                (self._df_item['value'] != '') &
                (~pd.isnull(self._df_item['value'])) &
                (self._df_item['value'] != -999999999)
        )

    @staticmethod
    def rename_feature(feature_name, starting_string='f', new_string='s'):
        starting_string = starting_string + '__'
        new_string = new_string + '__'
        new_variable_name = feature_name.replace(starting_string, new_string) \
            if feature_name.startswith(starting_string) else feature_name
        return new_variable_name

    @property
    def df_item(self):
        for method_name in self.get_make_methods(method_type='feature', level='item'):
            feature_name = method_name.replace('make_feature_item', 'f')
            if feature_name in self._allowed_features and feature_name not in self._df_item.columns:
                try:
                    print(f"Processing {feature_name}...")
                    getattr(self, method_name)(feature_name)
                    # print(f"{feature_name} Processed")
                except Exception as e:
                    print("ERROR ON FEATURE ITEM: {}, It won't be used in further calculation".format(feature_name))
        return self._df_item

    @property
    def df_unit(self):
        for method_name in self.get_make_methods(method_type='feature', level='unit'):
            feature_name = method_name.replace('make_feature_unit', 'f')
            if feature_name in self._allowed_features and feature_name not in self._df_unit.columns:
                try:
                    print(f"Processing {feature_name} ...")
                    getattr(self, method_name)(feature_name)
                except Exception as e:
                    print("ERROR ON FEATURE UNIT: {}, It won't be used in further calculation".format(feature_name))
        return self._df_unit

    @property
    def df_active_paradata(self):
        # df_para_active, active events, prior rejection/review events, for questions with scope interviewer

        active_events = ['InterviewCreated', 'AnswerSet', 'Resumed', 'AnswerRemoved', 'CommentSet', 'Restarted']
        # only keep events done by interview (in most cases this should be all, after above filters,
        # just in case supervisor or HQ answered something while interviewer answered on web mode)
        # keep active events, prior rejection/review events, for questions with scope interviewer
        active_mask = (self.df_paradata['event'].isin(active_events)) & \
                      (self.df_paradata['question_scope'].isin([0, ''])) & \
                      (self.df_paradata['role'] == 1)

        vars_needed = ['interview__id', 'order', 'event', 'responsible', 'role', 'tz_offset',
                       'param', 'answer', 'roster_level', 'timestamp_local', 'variable_name',
                       'question_sequence', 'question_scope', 'type', 'question_type',
                       'survey_name', 'survey_version', 'interviewing', 'yes_no_view', 'index_col', 'f__answer_time_set'
                       ]

        df_para_active = self.df_paradata.loc[active_mask, vars_needed]
        return df_para_active

    @property
    def df_paradata(self):
        return self._df_paradata

    @property
    def df_microdata(self):
        paradata, questionaire, microdata = self.get_dataframes(reload=self.config['reload'],
                                                                save_to_disk=self.config['save_to_disk'])
        return microdata

    @property
    def df_questionaire(self):
        paradata, questionaire, microdata = self.get_dataframes(reload=self.config['reload'],
                                                                save_to_disk=self.config['save_to_disk'])
        return questionaire

    def make_index_col(self, df, columns=None):
        if columns is None:
            columns = self.item_level_columns

        # define internal variable for level columns
        def merge_columns(row, select_columns):
            return '_'.join(
                [str(row[col]) for col in select_columns if pd.isnull(row[col]) is False and row[col] != ''])

        df['index_col'] = df[columns].apply(merge_columns, args=(columns,), axis=1)
        return df

    def make_df_item(self, microdata):

        microdata = self.make_index_col(microdata)
        df_item = microdata[['value', 'type', 'is_integer', 'qnr_seq',
                             'n_answers', 'answer_sequence',
                             'cascade_from_question_id', 'is_filtered_combobox',
                             'index_col'] + self.item_level_columns].copy()

        paradata_columns = ['responsible', 'f__answer_time_set', 'interviewing', 'tz_offset']
        # merge microdata with active pardata and keep only the last answer set
        answer_set_mask = (self.df_active_paradata['event'] == 'AnswerSet')
        data = self.df_active_paradata[answer_set_mask].drop_duplicates(subset='index_col', keep='last')
        df_item = df_item.merge(data[paradata_columns + ['index_col']], how='left',
                                on='index_col')
        # Remove items that arew not in interviewing
        df_item = df_item[df_item['interviewing'] == True]
        df_item = self.add_sequence_features(df_item)

        df_item = self.add_item_time_features(df_item)

        return df_item.copy()

    def add_sequence_features(self, df_item):
        # Define the list of features depending on sequences
        sequence_features = ['f__previous_question', 'f__previous_answer',
                             'f__previous_roster', 'f__sequence_jump']
        if any(col in self._allowed_features for col in sequence_features):
            df_sequence = self.get_df_sequence()
            # Remove non-selected features
            sequence_features = ['index_col'] + [f for f in sequence_features if f in self._allowed_features]
            df_sequence = df_sequence[sequence_features]
            # Merge with df_item

            df_item = df_item.merge(df_sequence, how='left', on='index_col')
        return df_item

    def add_item_time_features(self, df_item):
        # Define the list of features depending on time
        time_features = ['f__answer_duration', 'f__comment_duration']
        if any(col in self._allowed_features for col in time_features):
            df_time = self.get_df_time()
            # Remove records that have variable_name as empty string, i.e. Pauses
            df_time = df_time[df_time['variable_name'] != '']
            # summarize on item level
            df_time = df_time.groupby(self.item_level_columns + ['index_col']).agg(
                f__answer_duration=('f__answer_duration', 'sum'),
                f__comment_duration=('f__comment_duration', 'sum'),
            ).reset_index()

            # Remove non-selected features
            time_features = ['index_col'] + [f for f in time_features if f in self._allowed_features]
            df_time = df_time[time_features]
            # Merge with df_item
            df_item = df_item.merge(df_time, how='left', on='index_col')
        return df_item

    def get_df_time(self):
        # f__answer_duration, total time spent to record answers, i.e.,
        # sum of all time-intervals from active events ending with the item being AnswerSet or AnswerRemoved
        # f__comment_duration, total time spent to comment, i.e.,
        # sum of all time-intervals from active events ending with the item being CommentSet
        ###### ITEM features
        df_time = self.df_active_paradata.copy()

        # calculate time difference in seconds
        df_time['time_difference'] = df_time.groupby('interview__id')['timestamp_local'].diff()
        df_time['time_difference'] = df_time['time_difference'].dt.total_seconds()
        df_time['f__time_changed'] = np.where(df_time['time_difference'] < -180, df_time['time_difference'], np.nan)
        df_time.loc[df_time['time_difference'] < 0, 'time_difference'] = pd.NA
        # time for answers/comments
        df_time['f__answer_duration'] = df_time.loc[
            df_time['event'].isin(['AnswerSet', 'AnswerRemoved']), 'time_difference']
        df_time['f__comment_duration'] = df_time.loc[df_time['event'] == 'CommentSet', 'time_difference']

        ###### UNIT features
        active_events = ['AnswerSet', 'AnswerRemoved', 'CommentSet', 'Resumed', 'Restarted']

        df_time['f__total_duration'] = df_time.loc[(df_time['event'].isin(active_events) & (
                df_time['time_difference'] < 30 * 60)), 'time_difference']

        # Get the min date from the min question sequesce as there might be some time setting
        # change later that would change the starting date if just looking at the min of timestamp_local
        min_date = \
        df_time[(df_time['question_sequence'] == df_time[df_time['variable_name'] != '']['question_sequence'].min())][
            'timestamp_local'].min()
        # max_date = df_time[df_time['question_sequence'] == df_time['question_sequence'].max()]['timestamp_local'].max()
        df_time['f__days_from_start'] = abs(
            (df_time['timestamp_local'] - min_date).dt.days)  # / (max_date-min_date).days

        return df_time

    def get_df_sequence(self):

        df_last = self.df_active_paradata[self.df_active_paradata['event'] == 'AnswerSet'].groupby(
            'index_col').last()
        df_last = df_last.sort_values(['interview__id', 'order']).reset_index()

        # f__previous_question, f__previous_answer, f__previous_roster for previous answer set
        df_last['f__previous_question'] = df_last.groupby('interview__id')['variable_name'].shift(
            fill_value=pd.NA)
        df_last['f__previous_answer'] = df_last.groupby('interview__id')['answer'].shift(
            fill_value='')
        df_last['f__previous_roster'] = df_last.groupby('interview__id')['roster_level'].shift(
            fill_value='')
        # f__sequence_jump, Difference between actual answer sequence and
        # question sequence in the questionnaire, in difference to previous question
        df_last['answer_sequence'] = df_last.groupby('interview__id').cumcount() + 1
        df_last['diff'] = df_last['question_sequence'] - df_last['answer_sequence']
        df_last['f__sequence_jump'] = df_last.groupby('interview__id')['diff'].diff()

        return df_last

    def process_paradata(self, paradata):

        # streamline missing (empty, NaN) to '', important to identify duplicates in terms of the roster below
        paradata.fillna('', inplace=True)

        paradata['f__answer_time_set'] = (paradata['timestamp_local'].dt.hour + paradata[
            'timestamp_local'].dt.round(
            '30min').dt.minute / 60)

        # interviewing, True prior to Supervisor/HQ interaction, else False
        events_split = ['RejectedBySupervisor', 'OpenedBySupervisor', 'OpenedByHQ', 'RejectedByHQ']
        # Create a flag indicating whether each row has an event in `events_split`
        paradata['flag'] = paradata['event'].isin(events_split)

        # Use `groupby` and `cumsum` to count how many flagged events occur for each group
        # If the count is greater than 0, then the 'interviewing' column should be False
        paradata['cumulative_flag'] = paradata.groupby('interview__id')['flag'].cumsum()
        paradata['interviewing'] = np.where(paradata['cumulative_flag'] > 0, False, True)

        # Cleanup the intermediate columns
        paradata.drop(['flag', 'cumulative_flag'], axis=1, inplace=True)
        paradata = paradata[(paradata['interviewing'] == True)].copy()

        paradata = self.make_index_col(paradata)
        paradata.sort_values(['interview__id', 'order'], inplace=True)
        paradata.reset_index(inplace=True)
        return paradata

    def make_df_unit(self):
        df_unit = self.df_active_paradata[['interview__id', 'responsible', 'survey_name', 'survey_version']].copy()
        df_unit.drop_duplicates(inplace=True)
        df_unit = df_unit[(df_unit['responsible'] != '') & (~pd.isnull(df_unit['responsible']))]
        df_unit = self.add_pause_features(df_unit)
        df_unit = self.add_unit_time_features(df_unit)
        return df_unit

    def save_data(self, df, file_name):

        target_dir = os.path.join(self.config.data.raw, self.config.surveys)
        survey_path = os.path.join(target_dir, self.config.survey_version)
        processed_data_path = os.path.join(survey_path, 'processed_data')
        df.to_pickle(os.path.join(processed_data_path, f'{file_name}.pkl'))

    def get_make_methods(self, method_type='feature', level='item'):
        return [method for method in dir(self) if method.startswith(f"make_{method_type}_{level}__")
                and callable(getattr(self, method))]

    ###### Feature item methods
    def make_feature_item__string_length(self, feature_name):
        # f__string_length, length of string answer, if TextQuestions else empty pd.NA
        text_question_mask = (self._df_item['type'] == 'TextQuestion')
        self._df_item[feature_name] = pd.NA
        self._df_item.loc[text_question_mask, feature_name] = self._df_item.loc[
            text_question_mask, 'value'].str.len().astype('Int64')

    def make_feature_item__numeric_response(self, feature_name):
        # f__numeric_response, response, if NumericQuestions, else empty pd.NA
        self._df_item[feature_name] = np.nan
        self._df_item.loc[self.numeric_question_mask, feature_name] = \
            self._df_item[self.numeric_question_mask]['value'].astype(
                float)

    def make_feature_item__first_digit(self, feature_name):
        # f__first_digit, first digit of the response if numeric question else empty pd.NA
        self._df_item[feature_name] = pd.NA
        self._df_item.loc[self.numeric_question_mask, feature_name] = \
            pd.to_numeric(self._df_item.loc[self.numeric_question_mask, 'value']).abs().astype(str).str[0].astype(
                'Int64')

    def make_feature_item__last_digit(self, feature_name):
        # f__last_digit, modulus of 10 of the response if numeric question else empty pd.NA
        self._df_item[feature_name] = pd.NA

        def extract_last_digit(x):
            if x >= 1:  # Check if the value has at least two digits
                return x % 10  # Return the last digit
            else:
                return pd.NA

        self._df_item.loc[self.numeric_question_mask, feature_name] = pd.to_numeric(
            self._df_item.loc[self.numeric_question_mask, 'value']).astype('int64')

        self._df_item.loc[self.numeric_question_mask, feature_name] = self._df_item.loc[
            self.numeric_question_mask, feature_name].apply(extract_last_digit)

    def make_feature_item__first_decimal(self, feature_name):
        # f__first_decimal, first decimal digit if numeric question else empty pd.NA
        decimal_question_mask = (self._df_item['is_integer'] == False) & (self._df_item['value'] != '')
        self._df_item[feature_name] = pd.NA
        values = self._df_item.loc[decimal_question_mask, 'value'].astype(float)
        self._df_item.loc[decimal_question_mask, feature_name] = np.floor(values * 100) % 100
        self._df_item[feature_name] = self._df_item[feature_name].astype('Int64')

    def make_feature_item__answer_position(self, feature_name):
        # f__rel_answer_position, relative position of the selected answer
        # only questions with more than two answers
        single_question_mask = ((self._df_item['type'] == 'SingleQuestion')
                                & (self._df_item['n_answers'] > 2)
                                & (self._df_item['is_filtered_combobox'] == False)
                                & (pd.isnull(self._df_item['cascade_from_question_id'])))

        def answer_position(row):
            value = None
            if (row['value'] in row['answer_sequence']) and pd.notnull(row['value']):
                value = round(row['answer_sequence'].index(row['value']) / (row['n_answers'] - 1), 3)
            return value

        self._df_item.loc[single_question_mask, feature_name] = (
            self._df_item.loc[single_question_mask].apply(answer_position, axis=1))

    def get_feature_item__answer_removed(self, feature_name):
        # This method cannot be used to directly insert the feature within df_item as the item
        # might no longer exist in microdata, but only in paradta
        # f__answer_removed, answers removed (by interviewer, or by system as a result of interviewer action).
        removed_mask = (self.df_paradata['event'] == 'AnswerRemoved') & (self.df_paradata['role'] == 1)
        df_item_removed = self.df_paradata[removed_mask]

        df_item_removed = df_item_removed.groupby(['interview__id', 'responsible', 'variable_name', 'qnr_seq', ]).agg(
            f__answer_removed=('order', 'count'),
        )
        return df_item_removed.reset_index()

    def make_feature_item__answer_changed(self, feature_name):

        df_changed_temp = self.df_active_paradata[self.df_active_paradata['event'] == 'AnswerSet']
        df_changed_temp[feature_name] = False

        # list and multi-select questions (without yes_no_mode)
        list_mask = (df_changed_temp['type'] == 'TextListQuestion')
        multi_mask = (df_changed_temp['yes_no_view'] == False)
        df_changed_temp['answer_list'] = pd.NA
        df_changed_temp.loc[list_mask, 'answer_list'] = df_changed_temp.loc[list_mask, 'answer'].str.split('|')
        df_changed_temp.loc[multi_mask, 'answer_list'] = df_changed_temp.loc[multi_mask, 'answer'].str.split(
            ', |\\|')
        df_changed_temp['prev_answer_list'] = df_changed_temp.groupby(self.item_level_columns + ['index_col'])[
            'answer_list'].shift()
        answers_mask = df_changed_temp['prev_answer_list'].notna()
        df_changed_temp.loc[answers_mask, feature_name] = df_changed_temp.loc[answers_mask].apply(
            lambda row: not set(row['prev_answer_list']).issubset(set(row['answer_list'])), axis=1)

        # single answer question
        df_changed_temp['prev_answer'] = df_changed_temp.groupby(self.item_level_columns + ['index_col'])[
            'answer'].shift()
        single_answer_mask = (~df_changed_temp['type'].isin(['MultyOptionsQuestion', 'TextListQuestion'])) & \
                             (df_changed_temp['prev_answer'].notna()) & \
                             (df_changed_temp['answer'] != df_changed_temp['prev_answer'])
        df_changed_temp.loc[single_answer_mask, feature_name] = True

        # yes_no_view questions
        yesno_mask = (df_changed_temp['yes_no_view'] == True)
        df_filtered = df_changed_temp[yesno_mask].copy()
        df_filtered[['yes_list', 'no_list']] = df_filtered['answer'].str.split('|', expand=True)
        df_filtered['yes_list'] = df_filtered['yes_list'].str.split(', ').apply(
            lambda x: [] if x == [''] or x is None else x)
        df_filtered['no_list'] = df_filtered['no_list'].str.split(', ').apply(
            lambda x: [] if x == [''] or x is None else x)
        df_filtered['prev_yes_list'] = df_filtered.groupby(self.item_level_columns + ['index_col'])['yes_list'].shift(
            fill_value=[])
        df_filtered['prev_no_list'] = df_filtered.groupby(self.item_level_columns + ['index_col'])['no_list'].shift(
            fill_value=[])
        df_changed_temp.loc[yesno_mask, feature_name] = df_filtered.apply(
            lambda row: not set(row['prev_yes_list']).issubset(set(row['yes_list'])), axis=1)
        df_changed_temp.loc[yesno_mask, feature_name] = df_filtered.apply(
            lambda row: not set(row['prev_no_list']).issubset(set(row['no_list'])), axis=1)

        # count on item level
        df_changed_temp = df_changed_temp.groupby('index_col')[feature_name].sum().reset_index()
        self._df_item[feature_name] = self._df_item['index_col'].map(
            df_changed_temp.set_index('index_col')[feature_name])

    def make_feature_item__answer_selected(self, feature_name):
        # f__answers_selected, number of answers selected in a multi-answer or list question
        multi_list_mask = self._df_item['type'].isin(['MultyOptionsQuestion', 'TextListQuestion'])

        # Function to calculate the number of elements in a list or return nan
        def count_elements_or_nan(val):
            if isinstance(val, list):
                return len(val)
            else:
                return np.nan

        self._df_item.loc[multi_list_mask, feature_name] = self._df_item.loc[multi_list_mask, 'value'].apply(
            count_elements_or_nan)
        # f__share_selected, share between answers selected, and available answers (only for unlinked questions)
        # TODO! confirm that it makes sense to use just put f__answer_share_selected in place of f__answer_selected
        self._df_item[feature_name] = self._df_item[feature_name] / self._df_item['n_answers']

    def make_feature_item__comment_length(self, feature_name):
        # f__comment_length
        comment_mask = (self.df_paradata['event'] == 'CommentSet') & \
                       (self.df_paradata['role'] == 1)

        df_item_comment = self.df_paradata[comment_mask].copy()
        df_item_comment[feature_name] = df_item_comment['answer'].str.len()
        df_item_comment = df_item_comment.groupby('index_col').agg(
            f__comment_length=(feature_name, 'sum'),
        )
        self._df_item[feature_name] = self._df_item['index_col'].map(
            df_item_comment[feature_name])

    def make_feature_item__comment_set(self, feature_name):
        # f__comments_set
        comment_mask = (self.df_paradata['event'] == 'CommentSet') & \
                       (self.df_paradata['role'] == 1)

        df_item_comment = self.df_paradata[comment_mask].copy()
        df_item_comment = df_item_comment.groupby('index_col').agg(
            f__comment_set=('order', 'count'),
        )
        self._df_item[feature_name] = self._df_item['index_col'].map(
            df_item_comment[feature_name])

    def make_feature_item__gps(self, feature_name):
        # f__gps_latitude, f__gps_longitude, f__gps_accuracy
        gps_mask = self._df_item['type'] == 'GpsCoordinateQuestion'
        gps_df = self._df_item.loc[gps_mask, 'value'].str.split(',', expand=True)
        gps_df.columns = ['gps__Latitude', 'gps__Longitude', 'gps__Accuracy', 'gps__altitude', 'gps__timestamp_utc']
        self._df_item[feature_name] = False
        self._df_item.loc[gps_mask, feature_name] = True
        self._df_item.loc[gps_mask, 'f__gps_latitude'] = pd.to_numeric(gps_df['gps__Latitude'], errors='coerce')
        self._df_item.loc[gps_mask, 'f__gps_longitude'] = pd.to_numeric(gps_df['gps__Longitude'], errors='coerce')
        self._df_item.loc[gps_mask, 'f__gps_accuracy'] = pd.to_numeric(gps_df['gps__Accuracy'], errors='coerce')
        drop_columns = [col for col in self._df_item.columns if col.startswith('gps__')]
        self._df_item.drop(columns=drop_columns, inplace=True)

    ##### UNIT item methods

    def make_feature_unit__number_answered(self, feature_name):
        answer_set_mask = ((~pd.isnull(self._df_item['value']))
                           & (self._df_item['value'] != -999999999)
                           & (self._df_item['value'] != '##N/A##')
                           & (self._df_item['value'] != '')
                           & (self._df_item['type'] != 'Variable')
                           )
        df_answer_set = self._df_item[answer_set_mask]
        df_answer_set = df_answer_set.groupby('interview__id').agg(
            f__number_answered=('value', 'count')
        )
        self._df_unit[feature_name] = self._df_unit['interview__id'].map(
            df_answer_set[feature_name])
        self._df_unit[feature_name].fillna(0, inplace=True)

    def make_feature_unit__number_unanswered(self, feature_name):
        answer_unset_mask = (
                                    (self._df_item['value'] == -999999999)
                                    | (self._df_item['value'] == '##N/A##')
                            ) & (self._df_item['type'] != 'Variable')
        df_answer_set = self._df_item[answer_unset_mask]
        df_answer_set = df_answer_set.groupby('interview__id').agg(
            f__number_unanswered=('value', 'count')
        )
        self._df_unit[feature_name] = self._df_unit['interview__id'].map(
            df_answer_set[feature_name])
        # Set to zero if not answered is not present
        self._df_unit[feature_name].fillna(0, inplace=True)

    def make_feature_unit__translation_positions(self, feature_name):

        trans_mask = (self.df_paradata['event'].isin(['AnswerSet', 'TranslationSwitched']))

        df_trans_temp = self.df_paradata.loc[
            trans_mask, ['interview__id', 'order', 'event', 'param']].copy().reset_index()
        df_trans_temp['seq'] = df_trans_temp.groupby('interview__id').cumcount() + 1

        # Define a function to calculate the relative positions
        def relative_translation_positions(group):
            total_rows = len(group)
            translation_position = group.loc[group['event'] == 'TranslationSwitched', 'seq']
            relative_positions = [pos / total_rows for pos in translation_position]
            return relative_positions

        # Group by 'interview__id' and apply the function
        df_trans_temp = df_trans_temp.groupby('interview__id').apply(
            relative_translation_positions).reset_index().rename(columns={0: feature_name})

        self._df_unit[feature_name] = self._df_unit['interview__id'].map(
            df_trans_temp.set_index('interview__id')[feature_name])

    def add_pause_features(self, df_unit):
        # Define the list of features depending on sequences
        pause_features = ['f__pause_count', 'f__pause_duration',
                          'f__pause_list']
        if any(col in self._allowed_features for col in pause_features):
            df_pause = self.get_df_pause()
            # Remove non-selected features
            pause_features = ['interview__id'] + [f for f in pause_features if f in self._allowed_features]
            df_pause = df_pause[pause_features]
            # Merge with df_item

            df_unit = df_unit.merge(df_pause, how='left', on='interview__id')
        return df_unit

    def get_df_pause(self):
        # f__pause_count, f__pause_duration, f__pause_list

        pause_mask = (self.df_paradata['role'] == 1)

        df_paused_temp = self.df_paradata[pause_mask][
            ['interview__id', 'order', 'event', 'timestamp_local', 'interviewing']].copy()
        df_paused_temp['prev_event'] = df_paused_temp.groupby('interview__id')['event'].shift(fill_value='')
        df_paused_temp['prev_datetime'] = df_paused_temp.groupby('interview__id')['timestamp_local'].shift()

        pause_mask = (df_paused_temp['event'].isin(['Restarted', 'Resumed']) &
                      df_paused_temp['prev_event'].isin(['Paused']))

        df_paused_temp = df_paused_temp.loc[pause_mask]
        df_paused_temp['pause_duration'] = df_paused_temp['timestamp_local'] - df_paused_temp['prev_datetime']

        df_paused_temp['pause_seconds'] = df_paused_temp['pause_duration'].dt.total_seconds().astype('Int64')
        df_paused_temp.loc[df_paused_temp['pause_seconds'] < 0, 'pause_seconds'] = pd.NA
        df_paused_temp = df_paused_temp.groupby('interview__id').agg(
            f__pause_count=('pause_seconds', 'size'),  # Count all occurrences
            f__pause_duration=('pause_seconds', 'sum'),  # Sum non-null values
            f__pause_list=('pause_seconds', lambda x: x.tolist())
        )

        # #convert Pause duration into minutes
        # df_paused_temp['f__pause_duration'] = df_paused_temp['f__pause_duration']/60
        df_paused_temp = df_paused_temp.reset_index()
        return df_paused_temp

    def add_unit_time_features(self, df_unit):
        # Define the list of features depending on time
        time_features = ['f__total_duration', 'f__total_elapse', 'f__days_from_start', 'f__time_changed']
        if any(col in self._allowed_features for col in time_features):
            df_time = self.get_df_time()

            df_dur = df_time.groupby('interview__id').agg(
                f__total_duration=('f__total_duration', 'sum'),
                f__total_elapse=('timestamp_local', lambda x: (x.max() - x.min()).total_seconds()),
                f__time_changed=('f__time_changed', 'sum'),
                f__days_from_start=('f__days_from_start', 'min'),
            )

            df_dur = df_dur.reset_index()
            # Remove non-selected features
            time_features = ['interview__id'] + [f for f in time_features if f in self._allowed_features]
            df_dur = df_dur[time_features]

            # # convert total_duration and total_elapseinto minutes
            # df_dur['f__total_duration'] = df_dur['f__total_duration'] / 60
            # df_dur['f__total_elapse'] = df_dur['f__total_elapse'] / 60
            # Merge with df_item
            df_unit = df_unit.merge(df_dur, how='left', on='interview__id')
        return df_unit
