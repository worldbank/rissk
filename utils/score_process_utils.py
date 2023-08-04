import pandas as pd
import numpy as np
import os
from scipy.spatial import cKDTree
from utils.process_utils import *
from utils.general_utils import *
from sklearn.ensemble import IsolationForest
from sklearn.cluster import DBSCAN
from sklearn.decomposition import PCA
from sklearn.preprocessing import MinMaxScaler
import warnings
from pandas.errors import PerformanceWarning

warnings.filterwarnings('ignore', category=PerformanceWarning)


class UnitScore:

    def __init__(self, config, feature_class, unit_class=None):
        self._feature_class = feature_class
        self.df_features = self._feature_class.df_features
        self._unit_class = unit_class
        self.df_unit = self._unit_class.df_unit if unit_class is not None else None
        self.config = config
        self._df_score = self.df_features[['interview__id', 'responsible']].copy()
        self._df_score.drop_duplicates(inplace=True)
        self._df_score.dropna(subset=['responsible'], inplace=True)
        self._applied_methods = []

    @property
    def df_score(self):
        for method_name in self.get_make_methods(method_type='score'):
            if method_name not in self._applied_methods:
                self._applied_methods.append(method_name)
                try:
                    getattr(self, method_name)()
                except:
                    print(f"ERROR ON {method_name}. The score it won't be used")
        return self._df_score

    def get_make_methods(self, method_type='feature'):
        return [method for method in dir(self) if method.startswith(f"make_{method_type}__")
                and callable(getattr(self, method))]

    def save(self):
        df = self.df_score[['interview__id', 'responsible', 'unit_risk_score']].copy()
        df.sort_values('unit_risk_score', inplace=True)
        file_name = "_".join([self.config.surveys[0], self.config.survey_version[0], 'unit_risk_score']) + ".csv"
        output_path = os.path.join(self.config.data.results, file_name)
        df.to_csv(output_path, index=False)
        print(f'SUCCESS! you can find the unit_risk_score output file in {self.config.data.results}')

    def make_global_score(self):

        df = self.df_score[[col for col in self.df_score.columns if col.startswith('s__')]].copy()
        pca = PCA(n_components=0.99, whiten=True)

        # Conduct PCA
        df_pca = pca.fit_transform(df.fillna(-1))
        scaler = MinMaxScaler(feature_range=(0, 100))
        self.df_score['unit_risk_score'] = (df_pca * pca.explained_variance_ratio_).sum(axis=1)
        self.df_score['unit_risk_score'] = 100 - scaler.fit_transform(self.df_score[['unit_risk_score']])
        # self.df_score['unit_risk_score'] = df.sum(axis=1)

    def make_score__answer_time_set(self):

        model = IsolationForest(contamination=0.20, random_state=42)
        col = 'f__answer_time_set'  # Adjust contamination parameter as needed
        data = self.df_features[~pd.isnull(self.df_features[col])].copy()
        X = data[[col]]
        model.fit(X)
        data['prediction'] = model.predict(X)
        # find the time range in which lie normal value
        min_good_time_range, max_good_time_range = data[data['prediction'] == 1]['f__answer_time_set'].min(), \
 \
            data[data['prediction'] == 1]['f__answer_time_set'].max()
        mask = (data['f__answer_time_set'] >= min_good_time_range) & (data['f__answer_time_set'] <= max_good_time_range)
        # mark as not anomaly tthose that lie within the range
        data.loc[mask, 'prediction'] = 1
        # count number of anomalies per interview
        temp = (data[data['prediction'] == -1].groupby('interview__id')['responsible'].count() /
                data.groupby('interview__id')[
                    'responsible'].count()).reset_index()

        self._df_score['s__answer_time_set'] = self._df_score['interview__id'].map(
            temp.set_index('interview__id')['responsible'])

    def make_score__sequence_jump(self):
        col = 'f__sequence_jump'
        index_col = ['interview__id', 'roster_level', 'responsible']
        data = pd.pivot_table(data=self.df_features, index=index_col, columns='variable_name',
                              values=col, fill_value=np.NAN)
        data = data.reset_index()
        index_col = [col for col in index_col if col in data.columns]
        keep_columns, drop_columns = self.filter_columns(data, index_col)
        data = data[keep_columns].copy()
        data = find_anomalies(data, index_col=index_col)

        specific_columns = [col for col in data.columns if col not in index_col and col != 'total_jumps']
        data.fillna(0, inplace=True)

        data['total_jumps'] = data[specific_columns].sum(axis=1)
        temp = (data.groupby('interview__id').total_jumps.sum() / data.groupby(
            'interview__id').total_jumps.count()).reset_index()

        self._df_score['s__sequence_jump'] = self._df_score['interview__id'].map(
            temp.set_index('interview__id')['total_jumps'])

    def make_score__time_changed(self):
        col = 'f__time_changed'  # Adjust contamination parameter as needed
        temp = (self.df_features[self.df_features[col] < 0].groupby('interview__id')['responsible'].count() /
                self.df_features.groupby('interview__id')[
                    'responsible'].count()).reset_index()

        self._df_score['s__time_changed'] = self._df_score['interview__id'].map(
            temp.set_index('interview__id')['responsible'])

    def make_score__gps(self):
        index_col = ['interview__id', 'responsible']
        data = pd.pivot_table(data=self.df_features[(self.df_features['f__Accuracy'] != -999999999.0)], index=index_col,
                              columns='variable_name',
                              values=['f__Latitude', 'f__Longitude', 'f__Accuracy'], fill_value=np.NAN)
        data = data.reset_index()
        data.columns = [f'{col[0]}_{col[1]}'.rstrip('_') for col in data.columns]

        data = data.copy()
        # Convert lat, lon to 3D cartesian coordinates
        data['x'], data['y'], data['z'] = lat_lon_to_cartesian(data['f__Latitude_GPS'], data['f__Longitude_GPS'])

        # Convert accuracy from meters to kilometers
        data['accuracy'] = data['f__Accuracy_GPS'] / 1e6

        # Create KDTree
        tree = cKDTree(data[['x', 'y', 'z']])

        # Convert 10 meters to kilometers, the unit of the Earth's radius
        radius = 10 / 1e6

        # Query for counts accounting for accuracy
        counts = [len(tree.query_ball_point(xyz, r=radius + accuracy)) - 1 for xyz, accuracy in
                  zip(data[['x', 'y', 'z']].values, data['accuracy'])]

        data['proximity_counts'] = counts

        # Identify spatial outliers
        dbscan = DBSCAN(eps=0.3, min_samples=5)  # tune these parameters for your data
        dbscan.fit(data[['f__Latitude_GPS', 'f__Longitude_GPS']])

        # -1 indicates noise in the DBSCAN algorithm
        data['spatial_outlier'] = dbscan.labels_ == -1

        temp = (data[(data['proximity_counts'] > 0) | (data['spatial_outlier'] == True)].groupby('interview__id')[
                    'responsible'].count() /
                data.groupby('interview__id')[
                    'responsible'].count()).reset_index()

        self._df_score['s__gps'] = self._df_score['interview__id'].map(
            temp.set_index('interview__id')['responsible'])

    def make_score__number_answers(self):
        answer_per_interview_df = self._feature_class.df_active_paradata.groupby(
            'interview__id').variable_name.nunique()
        answer_per_interview_df = answer_per_interview_df.reset_index()
        total_questions = \
        self._feature_class.df_questionaire[self._feature_class.df_questionaire['type'].str.contains('Question')][
            'type'].count()
        self._df_score['f__number_answers'] = self._feature_class._df_features['interview__id'].map(
            answer_per_interview_df.set_index('interview__id')['variable_name'] / total_questions)

    @staticmethod
    def filter_columns(data, index_col):
        drop_columns = []
        keep_columns = []
        total_interviews = data.interview__id.nunique()
        for col in data.columns:
            if (data[col].nunique() < 3 or data[
                col].count() / total_interviews < 0.2) and col not in index_col:
                drop_columns.append(col)
                # print(col, df_sequence_jump[col].count())
            else:
                # if (col not in ['interview__id','merging_column']) and abs(pivot_table__sequence_jump[col].skew())<1:
                #     pivot_table__sequence_jump[[col]] = pivot_table__sequence_jump[[col]].apply(np.log)
                keep_columns.append(col)
        return keep_columns, drop_columns
