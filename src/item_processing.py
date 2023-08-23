from src.feature_processing import *
from src.detection_algorithms import *
from src.utils.stats_utils import *
from scipy.spatial import cKDTree
from sklearn.cluster import DBSCAN
from pyod.models.ecod import ECOD
from pyod.models.cof import COF
from scipy import stats
from sklearn.preprocessing import StandardScaler


class ItemFeatureProcessing(FeatureProcessing):

    def __init__(self, config):
        super().__init__(config)

    @staticmethod
    def filter_columns(data, index_col, threshold=0.2):
        drop_columns = []
        keep_columns = []
        total_interviews = data.interview__id.nunique()
        for col in data.columns:
            if (data[col].nunique() < 3 or data[col].count() / total_interviews < threshold) and col not in index_col:
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

        data['s__proximity_counts'] = counts
        coords_columns = ['f__gps_latitude', 'f__gps_longitude']
        # Identify spatial outliers
        # model = DBSCAN(eps=0.3, min_samples=5)  # tune these parameters for your data
        # model.fit(data[coords_columns])

        model = COF()
        model.fit(data[coords_columns])
        # -1 indicates noise in the DBSCAN algorithm
        data['s__spatial_outlier'] = model.predict(data[coords_columns])#model.labels_
        #data['s__spatial_outlier'] = data['s__spatial_outlier'].replace({1: 0, -1: 1})

        return data.drop(columns=['x', 'y', 'z', 'accuracy'])

    def make_score__sequence_jump(self):
        feature_name = 'f__sequence_jump'
        data, index_col = self.get_clean_pivot_table(feature_name, remove_low_freq_col=True)
        data = find_anomalies(data, index_col=index_col)
        return data

    def make_score__first_decimal(self):
        feature = 'f__first_decimal'
        pivot_table, index_col = self.get_clean_pivot_table(feature, remove_low_freq_col=True)
        isolation_forest_model = IsolationForest(contamination=0.01)  # Adjust contamination parameter as needed
        for col in pivot_table.drop(columns=['interview__id', 'roster_level', 'responsible']).columns:
            pivot_table[col + feature.replace('f__', '__')] = None
            data = pivot_table[~pd.isnull(pivot_table[col])].copy()
            isolation_forest_model.fit(data[[col]])
            prediction = isolation_forest_model.predict(data[[col]])
            pivot_table.loc[~pd.isnull(pivot_table[col]), col + feature.replace('f__', '__')] = prediction
            pivot_table[col + feature.replace('f__', '__')] = pivot_table[col + feature.replace('f__', '__')].replace(
                {1: 0, -1: 1})
        return pivot_table

    def make_score__answer_time_set(self):
        # Detect time set anomalies using ECOD algorithm.
        # ECOD is a parameter-free, highly interpretable outlier detection algorithm based on empirical CDF functions
        feature_name = 'f__answer_time_set'
        score_name = feature_name.replace('f__', 's__')
        data = self.df_item[~pd.isnull(self.df_item[feature_name])].copy()
        contamination = self.config.features.answer_time_set.parameters.contamination
        model = ECOD(contamination=contamination)
        data[score_name] = model.fit_predict(data[[feature_name]])
        return data

    def make_score__answer_changed(self):
        feature_name = 'f__answer_changed'
        score_name = feature_name.replace('f__', 's__')
        data = self.df_item[~pd.isnull(self.df_item[feature_name])].copy()
        contamination = self.config.features.answer_changed.parameters.contamination
        model = ECOD(contamination=contamination)
        data[score_name] = model.fit_predict(data[['qnr_seq', feature_name]])
        return data

    def make_score__answer_removed(self):
        feature_name = 'f__answer_removed'
        score_name = feature_name.replace('f__', 's__')
        data = self.get_feature_item__answer_removed(feature_name)
        contamination = self.config.features.answer_removed.parameters.contamination
        model = ECOD(contamination=contamination)
        data[score_name] = model.fit_predict(data[['qnr_seq', feature_name]])
        return data

    def make_score__answer_position(self):
        # answer_position is calculated at responsible level
        feature = 'f__answer_position'
        pivot_table, index_col = self.get_clean_pivot_table(feature, remove_low_freq_col=True)
        for col in pivot_table.drop(columns=['interview__id', 'roster_level', 'responsible']).columns:
            data = pivot_table[~pd.isnull(pivot_table[col])].copy()

            unique_values = data[col].nunique()
            # Compute the entropy normalized by the number of possible values of the given distribution
            entropy_ = data.groupby('responsible')[col].apply(calculate_entropy) / np.log2(unique_values)
            pivot_table[col + feature.replace('f__', '__')] = pivot_table['responsible'].map(
                entropy_)
        return pivot_table

    def make_score__answer_selected(self):
        feature_name = 'f__answer_selected'
        pivot_table, index_col = self.get_clean_pivot_table(feature_name, remove_low_freq_col=True)
        for col in pivot_table.drop(columns=['interview__id', 'roster_level', 'responsible']).columns:
            data = pivot_table[~pd.isnull(pivot_table[col])].copy()
            pivot_table[col + feature_name.replace('f__', '__')] = False
            lower_outlier, upper_outlier = get_outlier_iqr(data, col)
            mask_lower = (~pd.isnull(pivot_table[col])) & (lower_outlier)
            mask_upper = (~pd.isnull(pivot_table[col])) & (upper_outlier)
            pivot_table.loc[mask_lower, col + feature_name.replace('f__', '__') + '_lower'] = True
            pivot_table.loc[mask_upper, col + feature_name.replace('f__', '__') + '_upper'] = True
        return pivot_table

    def make_score__answer_duration(self):

        feature_name = 'f__answer_duration'
        data, index_col = self.get_clean_pivot_table(feature_name, remove_low_freq_col=True)
        scaler = StandardScaler()
        columns = data.drop(columns=['interview__id', 'roster_level', 'responsible']).columns
        outliers_columns = ([col + feature_name.replace('f__', '__') + '_lower' for col in columns] +
                            [col + feature_name.replace('f__', '__') + '_upper' for col in columns])
        data = pd.concat([data, pd.DataFrame({col: None for col in outliers_columns}, index=data.index)], axis=1)

        # data[outliers_columns] = False
        for col in columns:
            X = detect_duration_outliers_by_magnitude(data, col)

            X[col + '_upper_outliers'] = X['is_outlier'].copy()
            # # Filter out outliers to compute box cox tranformation
            X = X[(X['is_outlier'] == False)].copy()
            if X[col].shape[0] > 0:
                box_cox_transformed_data, _ = stats.boxcox(X[col] + 1)
                X['box_cox'] = box_cox_transformed_data
                X['box_cox'] = transformed_data_rescaled = scaler.fit_transform(X[['box_cox']])
                # Define Threshold score and set lower and upper outliers, according to a threshold
                threshold = 1.5
                z_scores = stats.zscore(X['box_cox'].values)
                indices_lower_outliers = X[(np.abs(z_scores) > threshold) & (X[col] < X[col].median())].index
                indices_upper_outliers = X[(np.abs(z_scores) > threshold) & (X[col] > X[col].median())].index
                data.loc[~pd.isnull(data[col]), col + feature_name.replace('f__', '__') + '_lower'] = False
                data.loc[~pd.isnull(data[col]), col + feature_name.replace('f__', '__') + '_upper'] = False
                data.loc[indices_lower_outliers, col + feature_name.replace('f__', '__') + '_lower'] = True
                data.loc[indices_upper_outliers, col + feature_name.replace('f__', '__') + '_upper'] = True

        return data

    def make_score__single_question(self):
        feature = 'f__single_question'
        filter_condition = (self.df_item['type'] == 'SingleQuestion')
        pivot_table, index_col = self.get_clean_pivot_table('value', remove_low_freq_col=True,
                                                            filter_conditions=filter_condition)

        data = pd.DataFrame(pivot_table.responsible.unique(), columns=['responsible'])
        for col in pivot_table.drop(columns=['interview__id', 'roster_level', 'responsible']).columns:
            unique_values = pivot_table[col].nunique()
            entropy_ = pivot_table.groupby('responsible')[col].apply(calculate_entropy) / np.log2(unique_values)

            data[col + feature.replace('f__', '__')] = data['responsible'].map(entropy_)

        return data

    def make_score__multi_option_question(self):
        feature = 'f__multi_option_question'
        filter_condition = (self.df_item['type'] == 'MultyOptionsQuestion')
        data = self.df_item[filter_condition]
        pivot_table = pd.DataFrame(data.responsible.unique(), columns=['responsible'])
        for variable_name in data.variable_name.unique():
            mask = (data['variable_name'] == variable_name) & (data['value'] != '##N/A##')
            df_values = pd.get_dummies(data[mask]['value'].explode()).groupby(level=0).sum()

            # Joining back the exploded values to the original dataframe
            df = data[mask][['responsible', 'value']].drop('value', axis=1).join(df_values)

            # Function to calculate entropy
            def calculate_entropy(row):
                probabilities = row.mean() + 1e-10
                entropy = -np.sum(probabilities * np.log2(probabilities))
                return entropy

            # # Calculating entropy grouped by 'variable_name' and 'responsible'
            result = df.groupby(['responsible']).apply(calculate_entropy) / np.log2(df.shape[1] - 1)
            result = result.reset_index()
            result.columns = ['responsible', 'entropy']
            pivot_table[variable_name + feature.replace('f__', '__')] = pivot_table['responsible'].map(
                result.set_index('responsible')['entropy'])

        return pivot_table

    def make_score__first_digit(self):
        # answer_position is calculated at responsible level
        feature = 'f__first_digit'
        pivot_table, index_col = self.get_clean_pivot_table('f__numeric_response', remove_low_freq_col=True)
        columns = []
        for col in pivot_table.drop(columns=['interview__id', 'roster_level', 'responsible']).columns:
            data = pivot_table[~pd.isnull(pivot_table[col])].copy()
            new_col = filter_columns_by_magnitude(data.drop(columns=['interview__id', 'roster_level', 'responsible']),
                                                  3).columns
            columns += list(new_col)
        columns = list(set(columns))

        data = pd.DataFrame(pivot_table.responsible.unique(), columns=['responsible'])
        for col in columns:
            results_df = apply_benford_tests(pivot_table[['responsible'] + columns], 'responsible', col)
            results_df[col + feature.replace('f__', '__')] = results_df['p-value'].apply(lambda x: x <= 0.05)
            data[col + feature.replace('f__', '__')] = results_df['responsible'].map(
                results_df.set_index('responsible')[col + feature.replace('f__', '__')])

        return data

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
