import math
import pandas as pd
import numpy as np
from scipy.stats import entropy
from scipy import stats
from sklearn.preprocessing import StandardScaler
from scipy.stats import chisquare, fisher_exact
from collections import Counter


def benford_expected(n=100, data=None, numeric_col=None, apply_first_digit=True):
    """Return the expected counts for the first digit based on Benford's Law."""
    # you can adjust this as necessary
    if data is None:
        return [n * np.log10(1 + 1 / d) for d in range(1, 10)]
    else:
        clean_group = data[(~pd.isnull(data[numeric_col])) & (data[numeric_col] >= 1)]
        if apply_first_digit:
            actual = Counter(clean_group[numeric_col].apply(first_digit))
        else:
            actual = Counter(clean_group[numeric_col].apply(last_digit))
        return [n * actual[i] / len(clean_group) for i in range(1, 10)]


def first_digit(val):
    """Extract the first digit from a value."""
    return int(str(val)[0])


def last_digit(val):
    """Extract the first digit from a value."""
    return int(str(int(val))[-1])


def apply_benford_tests(data, responsible_col, numeric_col, apply_first_digit=True):
    """Apply either Fisher's or Chi-square test for Benford's Law on a numeric column grouped by a responsible."""
    results = []

    for responsible, group in data.groupby(responsible_col):
        # Drop NaN values for the current numeric column and consider only numeric values greater than 1
        clean_group = group[(~pd.isnull(group[numeric_col])) & (group[numeric_col] >= 1)]
        if apply_first_digit:
            actual = Counter(clean_group[numeric_col].apply(first_digit))
        else:
            actual = Counter(clean_group[numeric_col].apply(last_digit))

        actual = [actual[i] for i in range(1, 10)]

        # Adjust expected values based on the actual count of non-null values
        n = len(clean_group)
        if first_digit:
            expected_adjusted = benford_expected(n)
        else:
            expected_adjusted = benford_expected(n, data, numeric_col, apply_first_digit=apply_first_digit)

        # Decision between Chi-square and Fisher
        if np.any(np.array(expected_adjusted) < 5):
            # Use Fisher's Exact Test
            test_used = 'Fisher'
            p_value = fisher_exact(np.array([actual[:2], expected_adjusted[:2]]))[1]
        else:
            # Use Chi-square Test
            test_used = 'Chi-Squared'
            _, p_value = chisquare(actual, expected_adjusted)

        results.append((responsible, test_used, p_value))

    return pd.DataFrame(results, columns=[responsible_col, 'Test Used', 'p-value'])


def get_outlier_by_magnitude(series, mode_deviation=3, threshold_freq=0.02):
    """
    Detects values that are anomalies based on their order of magnitude.

    Args:
    - series (pd.Series): Series of numeric values.
    - mode_deviation (int): Maximum allowable deviation from the mode's order of magnitude.
    - threshold_freq (int): Maximum frequency for an order of magnitude to be considered anomalous.

    Returns:
    - pd.Series: Boolean Series with True for anomalies and False for normal values.
    """

    # Compute order of magnitude for each value
    min_value = series.min()
    if min_value<=0:
        order_of_magnitude = np.floor(np.log10(series + abs(min_value) + 1))
    else:
        order_of_magnitude = np.floor(np.log10(series))

    # Using Mode-based method
    mode_order = max(order_of_magnitude.mode().iloc[0], 1)

    mode_based_anomalies = (
            (order_of_magnitude < mode_order - mode_deviation) | (order_of_magnitude > mode_order + mode_deviation))

    # Using Histogram/Frequency count-based method
    freq_count = order_of_magnitude.value_counts() / series.count()
    anomalous_orders = freq_count[freq_count <= threshold_freq].index
    freq_based_anomalies = order_of_magnitude.isin(anomalous_orders)

    # Combine results
    anomalies = mode_based_anomalies | freq_based_anomalies

    return anomalies


def get_outlier_iqr(data, column_name):
    q_high = data[column_name].quantile(0.75)
    q_low = data[column_name].quantile(0.25)
    iqr = q_high - q_low
    lower_outlier = (data[column_name] < q_low - 1.5 * iqr) & (~pd.isnull(data[column_name]))
    upper_outlier = (data[column_name] > q_high + 1.5 * iqr) & (~pd.isnull(data[column_name]))
    return lower_outlier, upper_outlier


def get_outlier_z_score(data, column_name, threshold=2.5):
    # Compute the limits
    lower_limit = data[column_name].mean() - threshold * data[column_name].std()
    upper_limit = data[column_name].mean() + threshold * data[column_name].std()

    lower_outlier = (data[column_name] < lower_limit) & (~pd.isnull(data[column_name]))
    upper_outlier = (data[column_name] > upper_limit) & (~pd.isnull(data[column_name]))

    return lower_outlier, upper_outlier


def filter_columns_by_magnitude(df, min_order_of_magnitude=3):
    """
    Filters columns in a DataFrame that have values spanning at least min_order_of_magnitude.

    Parameters:
    - df: DataFrame to filter.
    - min_order_of_magnitude: Minimum span of orders of magnitude required to keep the column.

    Returns:
    - A DataFrame containing only the columns that meet the criterion.
    """

    # Define a function to calculate order of magnitude
    def order_of_magnitude(num):
        if num == 0:
            return 0
        elif num < 0:
            num = -num
        return int(math.floor(math.log10(num)))

    # Find columns that span at least min_order_of_magnitude
    valid_cols = []
    for col in df.columns:
        column_values = df[col].dropna()  # Remove NaNs to avoid issues
        if not column_values.empty:
            max_magnitude = order_of_magnitude(column_values.max())
            min_magnitude = order_of_magnitude(column_values.min())

            if max_magnitude - min_magnitude >= min_order_of_magnitude:
                valid_cols.append(col)

    return df[valid_cols]


def get_box_cox_rescaled(series):
    scaler = StandardScaler()
    min_value = series.min()
    box_cox = series
    if series.nunique() > 1:
        if min_value <= 0:
            box_cox = box_cox + abs(min_value) + 1
        box_cox, _ = stats.boxcox(box_cox)
        box_cox = scaler.fit_transform(box_cox.reshape(-1, 1))
    return box_cox


def calculate_entropy(column):
    # Calculate the entropy and multiply by the number of record
    # Value counts normalizes the counts to get probabilities
    prob_distribution = column.value_counts(normalize=True).values
    return entropy(prob_distribution) #* len(column)