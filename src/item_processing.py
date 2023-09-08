from src.feature_processing import *
from src.detection_algorithms import *
from src.utils.stats_utils import *
from scipy.spatial import cKDTree
from sklearn.cluster import DBSCAN
from pyod.models.ecod import ECOD
from pyod.models.cof import COF
from pyod.models.lof import LOF
from pyod.models.inne import INNE
from scipy import stats
from sklearn.preprocessing import StandardScaler
from pyod.models.thresholds import FILTER


class ItemFeatureProcessing(FeatureProcessing):

    def __init__(self, config):
        super().__init__(config)

    def get_contamination_parameter(self, feature_name, method='medfilt', random_state=42):
        f_name = feature_name.replace('f__', '')
        contamination = self.config.features.get(f_name, {}).get('parameters', {}).get('contamination')
        if contamination is None or contamination == 'auto' or self.config.automatic_contamination is True:
            return FILTER(method=method, random_state=random_state)
        else:
            return contamination

    @staticmethod
    def filter_variable_name_by_frequency(df, feature_name, frequency=100, min_unique_values=3):
        # Select only those variables that have at least 'min_unique_values' distinct values and more than one
        # 'frequency' records
        valid_variables = df.groupby('variable_name').filter(lambda group:
                                                             len(group[feature_name].unique()) >= min_unique_values
                                                             and len(group) > frequency)
        # Get the unique variable names that meet the conditions
        variables = valid_variables['variable_name'].unique()
        return variables

    @staticmethod
    def filter_columns(data, index_col, threshold=100):
        drop_columns = []
        keep_columns = []
        for col in data.columns:
            if (data[col].nunique() < 3 or data[col].count() < threshold) and col not in index_col:
                drop_columns.append(col)
            else:
                keep_columns.append(col)
        return keep_columns, drop_columns

    def get_clean_pivot_table(self, feature_name, remove_low_freq_col=True, filter_conditions=None, threshold=0.2):
        index_col = ['interview__id', 'roster_level', 'responsible']
        data = self.df_item
        if filter_conditions is not None:
            data = data.loc[filter_conditions]
        data = pd.pivot_table(data=data, index=index_col, columns='variable_name',
                              values=feature_name, fill_value=np.NAN)
        data = data.reset_index()
        # Define again index_col after pivoting in case of some column missing
        if data.columns.nlevels > 1:
            data.columns = [f'{col[0]}_{col[1]}'.rstrip('_') for col in data.columns]

        index_col = [col for col in index_col if col in data.columns]
        keep_columns, drop_columns = self.filter_columns(data, index_col, threshold=threshold)
        if remove_low_freq_col:
            data = data[keep_columns]

        return data, index_col

    def make_score__gps(self):
        feature_name = ['f__gps_latitude', 'f__gps_longitude', 'f__gps_accuracy']
        data, index_col = self.get_clean_pivot_table(feature_name, remove_low_freq_col=False)

        def replace_with_feature_name(columns, feature_names):
            for i, s in enumerate(columns):
                for sub in feature_names:
                    if sub in s:
                        columns[i] = sub
                        break
            return columns

        data.columns = replace_with_feature_name(list(data.columns), feature_name)
        data = data.reset_index()
        # Everything that has 0,0 as coordinates is an outlier
        data['s__gps_extreme_outlier'] = 0
        data['s__gps_extreme_outlier'] = data['f__gps_latitude'].apply(lambda x: 1 if x == 0.000000 else 0)
        data['s__gps_extreme_outlier'] = data['f__gps_longitude'].apply(lambda x: 1 if x == 0.000000 else 0)


        # Convert lat, lon to 3D cartesian coordinates
        data['x'], data['y'], data['z'] = lat_lon_to_cartesian(data['f__gps_latitude'],
                                                               data['f__gps_longitude'])

        # Convert accuracy from meters to kilometers
        data['accuracy'] = data['f__gps_accuracy'] / 1e6

        # Create KDTree
        tree = cKDTree(data[['x', 'y', 'z']])

        # Convert 10 meters to kilometers, the unit of the Earth's radius
        radius = 10 / 1e6

        # Query for counts accounting for accuracy
        counts = [len(tree.query_ball_point(xyz, r=radius + accuracy)) - 1 for xyz, accuracy in
                  zip(data[['x', 'y', 'z']].values, data['accuracy'])]

        data['s__gps_proximity_counts'] = counts
        coords_columns = ['x', 'y']
        # Identify extreme spatial outliers

        mask = (data['s__gps_extreme_outlier'] < 1)

        median_x = data[mask].drop_duplicates(subset='x')['x'].median()
        median_y = data[mask].drop_duplicates(subset='y')['y'].median()
        median_z = data[mask].drop_duplicates(subset='z')['z'].median()

        # Calculate distances from the median point
        data['distance_to_median'] = np.sqrt((data[mask]['x'] - median_x) ** 2 +
                                             (data[mask]['y'] - median_y) ** 2 +
                                             (data[mask]['z'] - median_z) ** 2
                                             )

        # Set a threshold (e.g., 95th percentile of distances)
        # Everything that is above 30 + the median distance is an outlier
        threshold = data[mask]['distance_to_median'].quantile(0.95) + 30
        data.loc[mask, 's__gps_extreme_outlier'] = data[mask]['distance_to_median'] > threshold

        # # Make a further cleaning with dbscan
        # coords_columns = ['x', 'y']
        # model = DBSCAN(eps=0.5, min_samples=5)
        # model.fit(data[mask][coords_columns])
        # data.loc[mask, 'outlier'] = model.fit_predict(data[mask][coords_columns])
        # data['s__gps_extreme_outlier'] = data.apply(
        #     lambda row: 1 if row['outlier'] == -1 or row['s__gps_extreme_outlier'] == 1 else 0, 1)

        # USE COF if dataset hase less than 20000 samples else use LOF
        contamination = self.get_contamination_parameter('f__gps', method='medfilt', random_state=42)
        if data[mask].shape[0] < 10000:
            model = COF(contamination=contamination)
        else:
            model = LOF(contamination=contamination, n_neighbors=20)
        model.fit(data[mask][coords_columns])
        data.loc[mask, 's__gps_outlier'] = model.predict(data[mask][coords_columns])

        return data.drop(columns=['x', 'y', 'z', 'accuracy', 'distance_to_median', 'outlier'], errors='ignore')

    def make_score__sequence_jump(self):
        feature_name = 'f__sequence_jump'
        score_name = self.rename_feature(feature_name)
        df = self.df_item[~pd.isnull(self.df_item[feature_name])].copy()
        # Select only those variables that have at least three distinct values and more than one hundred records
        valid_variables = self.filter_variable_name_by_frequency(df, feature_name, frequency=100, min_unique_values=3)
        df[score_name] = 0
        contamination = self.get_contamination_parameter(feature_name)
        for var in valid_variables:
            mask = (df['variable_name'] == var)
            model = INNE(contamination=contamination, random_state=42)
            model.fit(df[mask][[feature_name]])
            df.loc[mask, score_name] = model.predict(df[mask][[feature_name]])
        return df

    def make_score__first_decimal(self):

        feature_name = 'f__first_decimal'
        score_name = self.rename_feature(feature_name)
        df = self.df_item[~pd.isnull(self.df_item[feature_name])].copy()
        # Select only those variables that have at least three distinct values and more than one hundred records
        valid_variables = self.filter_variable_name_by_frequency(df, feature_name, frequency=100, min_unique_values=3)
        df[score_name] = 0
        for var in valid_variables:
            mask = (df['variable_name'] == var)
            contamination = self.get_contamination_parameter(feature_name, method='medfilt', random_state=42)
            model = COF(contamination=contamination)
            model.fit(df[mask][[feature_name]])
            df.loc[mask, score_name] = model.predict(df[mask][[feature_name]])
        return df

    def make_score__answer_hour_set(self):
        # Detect time set anomalies using ECOD algorithm.
        # ECOD is a parameter-free, highly interpretable outlier detection algorithm based on empirical CDF functions
        feature_name = 'f__answer_hour_set'
        score_name = self.rename_feature(feature_name)
        df = self.df_item[~pd.isnull(self.df_item[feature_name])]#.copy()

        # Sorting the DataFrame based on the 'frequency' answer_hour_set in descending order
        sorted_hours = df[feature_name].value_counts().index
        hour_to_rank = {hour: rank for rank, hour in enumerate(sorted_hours)}
        # Create a frequecy column
        df['frequency'] = df[feature_name].map(hour_to_rank)

        # IDENTIFY Outliers by ECOD anomaly detection model
        contamination = self.get_contamination_parameter(feature_name)
        model = ECOD(contamination=contamination)
        model.fit(df[[feature_name]])
        df[score_name] = model.predict(df[[feature_name]])

        # In case has detected "high frequencies anomalies", set them to 0
        df.loc[df['frequency'] <= df[df[score_name] == 0]['frequency'].min(), score_name] = 0
        df.drop(columns=['frequency'], inplace=True)
        return df

    def make_score__answer_changed(self):
        feature_name = 'f__answer_changed'
        score_name = self.rename_feature(feature_name)
        df = self.df_item[~pd.isnull(self.df_item[feature_name])]#.copy()
        # Select only those variables that have at least 1 distinct values and more than one hundred records
        valid_variables = self.filter_variable_name_by_frequency(df, feature_name, frequency=100, min_unique_values=1)
        df[score_name] = 0
        contamination = self.get_contamination_parameter(feature_name, method='medfilt', random_state=42)
        for var in valid_variables:
            mask = (df['variable_name'] == var)

            model = ECOD(contamination=contamination)
            model.fit(df[mask][[feature_name]])
            df.loc[mask, score_name] = model.predict(df[mask][[feature_name]])
        return df

    def make_score__answer_removed(self):
        feature_name = 'f__answer_removed'
        score_name = self.rename_feature(feature_name)
        df = self.get_feature_item__answer_removed(feature_name)
        # Select only those variables that have at least 1 distinct values and more than one hundred records
        valid_variables = self.filter_variable_name_by_frequency(df, feature_name, frequency=100, min_unique_values=1)
        df[score_name] = 0
        contamination = self.get_contamination_parameter(feature_name, method='medfilt', random_state=42)
        for var in valid_variables:
            mask = (df['variable_name'] == var)

            model = ECOD(contamination=contamination)
            model.fit(df[mask][[feature_name]])
            df.loc[mask, score_name] = model.predict(df[mask][[feature_name]])
        return df

    def make_score__answer_position(self):
        # answer_position is calculated at responsible level
        feature_name = 'f__answer_position'
        score_name = self.rename_feature(feature_name)

        df = self.df_item[~pd.isnull(self.df_item[feature_name])].copy()
        # Select only those variables that have at least three distinct values and more than one hundred records
        valid_variables = self.filter_variable_name_by_frequency(df, feature_name, frequency=100, min_unique_values=3)
        df[score_name] = 0
        for var in valid_variables:
            mask = (df['variable_name'] == var)
            unique_values = df[mask][feature_name].nunique()
            entropy_df = df[mask].groupby('responsible')[feature_name].apply(calculate_entropy,
                                                                             unique_values=unique_values,
                                                                             min_record_sample=10)
            entropy_df = entropy_df.reset_index()
            entropy_df = entropy_df[~pd.isnull(entropy_df[feature_name])]

            if entropy_df.shape[0] > 0:
                entropy_df.sort_values(feature_name, inplace=True, ascending=False)

                median_value = entropy_df[feature_name].median()

                median_value = entropy_df[feature_name].median()
                entropy_df[score_name] = entropy_df[feature_name].apply(
                    lambda x: 1 if x < median_value - 50 / 100 * median_value else 0)
                df.loc[mask, score_name] = df[mask]['responsible'].map(entropy_df.set_index('responsible')[score_name])
        return df

    def make_score__answer_selected(self):
        feature_name = 'f__answer_selected'
        score_name = self.rename_feature(feature_name)
        df = self.df_item[~pd.isnull(self.df_item[feature_name])].copy()
        # Select only those variables that have at least three distinct values and more than one hundred records
        valid_variables = self.filter_variable_name_by_frequency(df, feature_name, frequency=100, min_unique_values=3)
        df[score_name] = 0
        for var in valid_variables:
            mask = (df['variable_name'] == var)
            contamination = self.get_contamination_parameter(feature_name, method='medfilt', random_state=42)
            model = ECOD(contamination=contamination)
            model.fit(df[mask][[feature_name]])
            score_name1 = score_name + '_lower'
            score_name2 = score_name + '_upper'

            df.loc[mask, score_name] = model.predict(df[mask][[feature_name]])
            min_good_value = df[(df[score_name] == 0) & mask][feature_name].min()
            max_good_value = df[(df[score_name] == 0) & mask][feature_name].max()

            df.loc[mask, score_name1] = 0
            df.loc[mask, score_name2] = 0

            df.loc[mask & (df[mask][feature_name] < min_good_value), score_name1] = 1
            df.loc[mask & (df[mask][feature_name] > max_good_value), score_name2] = 1
            df.drop(columns=[score_name], inplace=True)
        return df

    def make_score__answer_duration(self):
        feature_name = 'f__answer_duration'
        score_name = self.rename_feature(feature_name)
        df = self.df_item[~pd.isnull(self.df_item[feature_name])]#.copy()
        # Select only those variables that have at least three distinct values and more than one hundred records
        valid_variables = self.filter_variable_name_by_frequency(df, feature_name, frequency=100, min_unique_values=3)

        score_name1 = score_name + '_lower'
        score_name2 = score_name + '_upper'

        df[score_name1] = 0
        df[score_name2] = 0
        for var in valid_variables:
            mask = (df['variable_name'] == var)
            contamination = self.get_contamination_parameter(feature_name, method='medfilt', random_state=42)
            model = ECOD(contamination=contamination)
            model.fit(df[mask][[feature_name]])

            df.loc[mask, score_name] = model.predict(df[mask][[feature_name]])

            min_good_value = df[(df[score_name] == 0) & mask][feature_name].min()
            max_good_value = df[(df[score_name] == 0) & mask][feature_name].max()

            df.loc[mask, score_name1] = 0
            df.loc[mask, score_name2] = 0

            df.loc[mask & (df[mask][feature_name] < min_good_value), score_name1] = 1
            df.loc[mask & (df[mask][feature_name] > max_good_value), score_name2] = 1

            df.drop(columns=[score_name], inplace=True)

        return df

    def make_score__single_question(self):
        # Answer single question is calculated at responsible level

        feature_name = 'f__single_question'
        score_name = self.rename_feature(feature_name)

        single_question_mask = ((self.df_item['type'] == 'SingleQuestion')
                                & (self.df_item['n_answers'] > 1)
                                & (self.df_item['is_filtered_combobox'] == False)
                                & (pd.isnull(self.df_item['cascade_from_question_id'])))

        df = self.df_item[single_question_mask].copy()
        # Select only those variables that have at least three distinct values and more than one hundred records

        variables = self.filter_variable_name_by_frequency(df, 'value', frequency=100, min_unique_values=3)
        df[score_name] = 0
        for var in variables:
            mask = (df['variable_name'] == var)
            unique_values = df[mask]['value'].nunique()
            entropy_df = df[mask].groupby('responsible')['value'].apply(calculate_entropy, unique_values=unique_values)
            entropy_df = entropy_df.reset_index()
            entropy_df = entropy_df[~pd.isnull(entropy_df['value'])]

            if entropy_df.shape[0] > 0:
                entropy_df.sort_values('value', inplace=True, ascending=False)

                median_value = entropy_df['value'].median()

                median_value = entropy_df['value'].median()
                entropy_df[score_name] = entropy_df['value'].apply(
                    lambda x: 1 if x < median_value - 50 / 100 * median_value else 0)
                df.loc[mask, score_name] = df[mask]['responsible'].map(entropy_df.set_index('responsible')[score_name])

        return df

    def make_score__multi_option_question(self):
        feature_name = 'f__multi_option_question'
        # Answer single question is calculated at responsible level

        score_name = self.rename_feature(feature_name)

        multi_question_mask = (self.df_item['type'] == 'MultyOptionsQuestion').copy()

        df = self.df_item[multi_question_mask].copy()
        # Select only those variables that have at least three distinct values and more than one hundred records
        valid_variables = df.groupby('variable_name').filter(lambda x: len(x) >= 100)
        # Get the unique variable names that meet the conditions
        variables = valid_variables['variable_name'].unique()

        df.loc[score_name] = 0
        for var in variables:
            mask = (df['variable_name'] == var)
            unique_values = len([v for v in df[mask]['value'].explode().unique() if v != '##N/A##'])
            entropy_df = df[mask].groupby('responsible')['value'].apply(calculate_list_entropy,
                                                                        unique_values=unique_values,
                                                                        min_record_sample=5)
            entropy_df = entropy_df.reset_index()
            entropy_df = entropy_df[~pd.isnull(entropy_df['value'])]

            if entropy_df.shape[0] > 0:
                entropy_df.sort_values('value', inplace=True, ascending=False)

                median_value = entropy_df['value'].median()

                median_value = entropy_df['value'].median()
                entropy_df[score_name] = entropy_df['value'].apply(
                    lambda x: 1 if x < median_value - 50 / 100 * median_value else 0)
                df.loc[mask, score_name] = df[mask]['responsible'].map(entropy_df.set_index('responsible')[score_name])

        return df

    def make_score__first_digit(self):
        feature_name = 'f__numeric_response'
        score_name = 's__first_digit'
        df = self.df_item[~pd.isnull(self.df_item[feature_name])].copy()
        # Select only those variables that have at least three distinct values and more than one hundred records
        valid_variables = self.filter_variable_name_by_frequency(df, feature_name, frequency=100, min_unique_values=3)

        # Select only those variables that have at least three different order of magnitude
        valid_variables = filter_variables_by_magnitude(df, feature_name, valid_variables, min_order_of_magnitude=3)

        # Computes the Jensen divergence for each variable_name and responsible on the first digit distribution.
        # Jensen's divergence returns a value between (0, 1) of how much the first digit distribution
        # of specific responsible is similar to the first digit distribution of all others.
        # Higher the value higher is the difference.
        # The Bendford Jensen divergence is calculated only on those responsible and variable_name
        # who have at least 50 records.
        # Once it is calculated, values that diverge from more than 50% from the median value get marked as "anomalus."
        benford_jensen_df = apply_benford_tests(df, valid_variables, 'responsible', feature_name,
                                                apply_first_digit=True, minimum_sample=50)

        df[score_name] = 0
        variable_list = benford_jensen_df['variable_name'].unique()
        for var in variable_list:

            bj_mask = (benford_jensen_df['variable_name'] == var) & (~pd.isnull(benford_jensen_df[feature_name]))
            bj_df = benford_jensen_df[bj_mask].copy()
            if bj_df.shape[0] > 0:
                bj_df.sort_values(feature_name, inplace=True, ascending=True)

                median_value = bj_df[feature_name].median()
                # If the distribution has a jensen difference grater than 50%
                # from the median value, mark it as "anomalus"
                bj_df[score_name] = bj_df[feature_name].apply(
                    lambda x: 1 if x > median_value + 50 / 100 * median_value else 0)


                mask = (df['variable_name'] == var)
                df.loc[mask, score_name] = df[mask]['responsible'].map(bj_df.set_index('responsible')[score_name])
        return df

    # def make_score__last_digit(self):
    #     feature = 'f__last_digit'
    #     pivot_table, index_col = self.get_clean_pivot_table('f__numeric_response', remove_low_freq_col=True)
    #     columns = []
    #     for col in pivot_table.drop(columns=['interview__id', 'roster_level', 'responsible']).columns:
    #         data = pivot_table[~pd.isnull(pivot_table[col])].copy()
    #         new_col = filter_columns_by_magnitude(data.drop(columns=['interview__id', 'roster_level', 'responsible']),
    #                                               3).columns
    #         columns += list(new_col)
    #     columns = list(set(columns))
    #
    #     data = pd.DataFrame(pivot_table.responsible.unique(), columns=['responsible'])
    #     for col in columns:
    #         results_df = apply_benford_tests(pivot_table[['responsible'] + columns], 'responsible', col)
    #         results_df[col + feature.replace('f__', '__')] = results_df['p-value'].apply(lambda x: x <= 0.05)
    #         data[col + feature.replace('f__', '__')] = results_df['responsible'].map(
    #             results_df.set_index('responsible')[col + feature.replace('f__', '__')])
    #
    #     return data
