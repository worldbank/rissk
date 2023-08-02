import pandas as pd
import numpy as np
from sklearn.preprocessing import LabelEncoder
from sklearn.ensemble import IsolationForest
from sklearn.preprocessing import OneHotEncoder
from sklearn.neighbors import NearestNeighbors
from scipy.spatial import distance_matrix


def normalize_column_name(s):
    """
    This function converts any string with capital letters to a string all lowercase with a "_" before any previously capital letter.

    Parameters:
    s (str): The string to convert.

    Returns:
    new_s (str): The converted string.
    """
    new_s = ""
    for i, char in enumerate(s):
        if char.isupper():
            # Add underscore only if it's not the first or last character
            if i != 0 and i != len(s)-1:
                new_s += "_"
            new_s += char.lower()
        else:
            new_s += char
    return new_s


def lat_lon_to_cartesian(lat, lon, R=6371):
    """
    Convert lat, lon into 3D cartesian coordinates

    Parameters:
    lat, lon: latitude and longitude in degrees
    R: radius of the Earth (default is in kilometers)

    Returns:
    x, y, z: 3D cartesian coordinates
    """
    lat, lon = np.radians(lat), np.radians(lon)
    x = R * np.cos(lat) * np.cos(lon)
    y = R * np.cos(lat) * np.sin(lon)
    z = R * np.sin(lat)
    return x, y, z

def haversine(lat1, lon1, lat2, lon2):
    """Calculate the great circle distance in kilometers between two points
    on the earth (specified in decimal degrees)"""
    # convert decimal degrees to radians
    lon1, lat1, lon2, lat2 = map(np.radians, [lon1, lat1, lon2, lat2])

    # haversine formula
    dlon = lon2 - lon1
    dlat = lat2 - lat1
    a = np.sin(dlat/2)**2 + np.cos(lat1) * np.cos(lat2) * np.sin(dlon/2)**2
    c = 2 * np.arcsin(np.sqrt(a))
    r = 6371 # Radius of earth in kilometers. Use 3956 for miles. Determines return value units.
    return c * r


def check_distance(data, min_distance=20, lat='f__Latitude_GPS', lon='f__Longitude_GPS'):

    df = data.copy()
    df.reset_index(inplace=True)
    df['is_too_close'] = False

    # Calculate the pairwise distances between all GPS coordinates
    distances = distance_matrix(df[[lat, lon]].values, df[[lat, lon]].values)
    distances = np.triu(distances)  # Only keep the upper triangular part (excluding the diagonal)

    # Find pairs of coordinates that are closer than 20 meters
    too_close_indices = np.argwhere(distances < min_distance)

    # Update 'is_too_close' column based on the pairs of coordinates that are too close
    for i, j in too_close_indices:
        if i != j:
            df.at[i, 'is_too_close'] = True
            df.at[j, 'is_too_close'] = True
    return df


# Create a function to report the limits of the Z-Score
def z_score_limits(df, column_name):
    """ returns the upper and lower limits of the Z-score """

    # Compute the limits
    upper_limit = df[column_name].mean() + 3 * df[column_name].std()
    lower_limit = df[column_name].mean() - 3 * df[column_name].std()

    # Round and return the limits
    upper_limit = round(upper_limit, 2)
    lower_limit = round(lower_limit, 2)

    return lower_limit, upper_limit


def log_transformation_function(df, column_name):
    """ Conduct a log transformation of a variable """
    # Replace the values with log-transformed values
    df[[column_name]] = df[[column_name]].apply(np.log)


def fix_anomalies(data, col, threshold_percentage=0.3):
    # If same column value is marked according to a distinct responsible both 1 and -1 than unset all anomalies
    data['anomaly'] = data[col].replace(data.groupby(col)['anomaly'].max().to_dict())

    # same if there is more than 30% of responsible that have that anomaly, set it to one
    # Get all responsible that been marked anomalus for a specific value
    grouped_df = data[data['anomaly'] == -1].groupby(col)['responsible'].nunique().reset_index(name='count')
    # Compute the percentage
    grouped_df['anomaly_percentage'] = grouped_df['count'] / data['responsible'].nunique()
    update_anomalies_list = grouped_df[grouped_df['anomaly_percentage'] >= threshold_percentage][col].values
    data.loc[data[col].isin(update_anomalies_list), 'anomaly'] = 1
    return data


def find_anomalies(df, index_col=[ 'interview__id', 'roster_level', 'responsible']):

    index_col = [col for col in index_col if col in df.columns]
    df['index_col'] = df[index_col].apply(lambda row: '_'.join([str(row[col]) for col in index_col]), axis=1)

    for col in df.drop(columns = index_col + ['index_col']).columns:
        #    col = 'age_adult'#df_sequence_jump.columns[9]
        data = df[~pd.isnull(df[col])].copy()

        onehot_encoder = OneHotEncoder()
        responsible_encoded = onehot_encoder.fit_transform(data[['responsible']]).toarray()
        # Extract the 'jump' and 'responsible_label' columns as features
        #encoded_df = pd.DataFrame(responsible_encoded, columns=onehot_encoder.get_feature_names(['responsible']))
        encoded_df = pd.DataFrame(responsible_encoded, columns=onehot_encoder.get_feature_names_out(['responsible']))

        # Combine the one-hot encoded DataFrame with the original DataFrame (excluding 'responsible')
        encoded_df[col] = data[col].values
        X = encoded_df.values.copy()#data[[col, 'responsible_label']].copy()
        # Initialize and fit the Isolation Forest model
        model = IsolationForest(contamination=0.1, random_state=42)  # Adjust contamination based on your anomaly threshold
        #model = GaussianMixture(n_components=2, random_state=42)
        #model = HBOS(n_bins=5)
        #model = CBLOF(contamination=0.05, n_clusters=3)
        model.fit(X)
        # Predict the anomalies (1 for normal, -1 for anomalies)
        anomaly_predictions = model.predict(X)
        #anomaly_scores = model.decision_function(X)
        # Add the anomaly predictions as a new column in the DataFrame
        data['anomaly'] = anomaly_predictions
        #data['anomaly_scores'] = anomaly_predictions
        data = fix_anomalies(data, col, 0.6)
        data['anomaly'] = data['anomaly'].replace({1: 0, -1: 1})

        df[col] = df['index_col'].map(data.set_index('index_col')['anomaly'])

    df.drop(columns = ['index_col'], inplace=True)
    return df


def find_outliers(df, index_col = [ 'interview__id', 'roster_level', 'responsible']):
    df['index_col'] = df[index_col].apply(lambda row: '_'.join([str(row[col]) for col in index_col]), axis=1)

    for col in df.drop(columns = index_col + ['index_col']).columns:
        #    col = 'age_adult'#df_sequence_jump.columns[9]
        data = df[~pd.isnull(df[col])].copy()

        q_high = data[col].quantile(0.75)
        q_low = data[col].quantile(0.25)
        iqr = q_high - q_low
        data['anomaly'] = 0
        data.loc[(data[col] < q_low - 1.5 * iqr) | (data[col] > q_high + 1.5 * iqr), 'anomaly'] = 1

        df[col] = df['index_col'].map(data.set_index('index_col')['anomaly'])

    df.drop(columns = ['index_col'], inplace=True)
    return df

def find_consecutive_anomalies(df, index_col = [ 'interview__id', 'roster_level', 'responsible']):

    df['index_col'] = df[index_col].apply(lambda row: '_'.join([str(row[col]) for col in index_col]), axis=1)

    for col in df.drop(columns = index_col + ['index_col']).columns:
        #    col = 'age_adult'#df_sequence_jump.columns[9]
        data = df[~pd.isnull(df[col])].copy()

        q_high = data[col].quantile(0.75)
        q_low = data[col].quantile(0.25)
        iqr = q_high - q_low
        data['anomaly'] = 0
        data.loc[(data[col] < q_low - 1.5 * iqr) | (data[col] > q_high + 1.5 * iqr), 'anomaly'] = 1

        q_high = data[data['anomaly'] == 0][col].quantile(0.75)
        q_low = data[data['anomaly'] == 0][col].quantile(0.25)
        iqr = q_high - q_low
        data.loc[(data[col] < q_low - 1.5 * iqr), 'anomaly'] = 1

        #data = fix_anomalies(data, col, 0.6)

        df[col] = df['index_col'].map(data.set_index('index_col')['anomaly'])

    df.drop(columns = ['index_col'], inplace=True)
    return df


def find_gps_anomaly(df, index_col):
    df['index_col'] = df[index_col].apply(lambda row: '_'.join([str(row[col]) for col in index_col]), axis=1)
    #

    data = df[(~pd.isnull(df['f__Latitude_GPS'])) & (~pd.isnull(df['f__Longitude_GPS']))].copy()
    onehot_encoder = OneHotEncoder()
    responsible_encoded = onehot_encoder.fit_transform(data[['responsible_']]).toarray()
    # Extract the 'jump' and 'responsible_label' columns as features
    encoded_df = pd.DataFrame(responsible_encoded, columns=onehot_encoder.get_feature_names_out(['responsible_']))
    # # Combine the one-hot encoded DataFrame with the original DataFrame (excluding 'responsible')
    encoded_df['f__Latitude_GPS'] = data['f__Latitude_GPS'].values
    encoded_df['f__Longitude_GPS'] = data['f__Longitude_GPS'].values
    X = encoded_df.values.copy()  # data[[col, 'responsible_label']].copy()
    coordinates = data[['f__Latitude_GPS', 'f__Longitude_GPS']].copy()  # data[[col, 'responsible_label']].copy()

    # Create a Nearest Neighbors model
    k = 2  # Number of nearest neighbors to consider
    model = NearestNeighbors(n_neighbors=k)

    # Fit the model on the data
    model.fit(coordinates)

    # Sample GPS coordinates for query
    query_location = [[38.9072, -77.0369]]  # Washington, D.C.

    # Find the distance to the k-th nearest neighbor for the query location
    distances, indices = model.kneighbors(query_location)
    anomaly_threshold = distances[0][-1]

    # Calculate the anomaly score for the query location
    anomaly_score = distances[0][-1] - distances[0][-2]

    # Check if the query location is an anomaly
    is_anomaly = anomaly_score > anomaly_threshold



    # #anomaly_scores = model.decision_function(X)
    # # # Add the anomaly predictions as a new column in the DataFrame
    data['anomaly'] = anomaly_predictions
    # # #data['anomaly_scores'] = anomaly_predictions
    # data = fix_anomalies(data, col, 0.6)
    data['anomaly'] = data['anomaly'].replace({1: 0, -1: 1})
    #
    df['anomaly'] = df['index_col'].map(data.set_index('index_col')['anomaly'])
    df.drop(columns=['index_col'], inplace=True)
    return df



