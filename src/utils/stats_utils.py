import math
import pandas as pd
import numpy as np
from scipy.stats import entropy
from scipy import stats
from sklearn.preprocessing import StandardScaler
from scipy.stats import chisquare, fisher_exact
from collections import Counter
from scipy.stats.mstats import winsorize


def jensen_shannon_divergence(p, q):
    m = 0.5 * (p + q)
    return 0.5 * (entropy(p, m) + entropy(q, m))


def jensen_shannon_distance(p, q):
    return np.sqrt(jensen_shannon_divergence(p, q))


def get_digit_frequecies(df, feature_name, apply_first_digit, minimum_sampe=50):
    digit_mask = (df[feature_name] != 0)
    if apply_first_digit:
        total_digit_values = df[digit_mask][feature_name].apply(first_digit)
    else:
        total_digit_values = df[digit_mask][feature_name].apply(last_digit)
    total_digit_count = Counter(total_digit_values)
    total_digit_count = [total_digit_count.get(i, 0) for i in range(1, 10)]
    if sum(total_digit_count) < minimum_sampe:
        total_digit_freq = None
    else:
        total_digit_freq = [v / sum(total_digit_count) for v in total_digit_count]
    # DO not consider samples with size less than minimum_sampe

    return total_digit_freq


def first_digit(val):
    """Extract the first digit from a value."""
    val = abs(val)
    return int(str(val)[0])


def last_digit(val):
    """Extract the first digit from a value."""
    return int(str(int(val))[-1])


def apply_benford_tests(df, valid_variables, responsible_col, feature_name, apply_first_digit=True, minimum_sampe=50):
    responsible_list = df[responsible_col].unique()
    results = []
    for var in valid_variables:
        variable_mask = df['variable_name'] == var
        for resp in responsible_list:
            score = None
            resp_mask = (df[responsible_col] == resp)
            total_digit_count = get_digit_frequecies(df[variable_mask & (~resp_mask)], feature_name, apply_first_digit,
                                                     minimum_sampe=minimum_sampe)
            resp_digit_count = get_digit_frequecies(df[variable_mask & resp_mask], feature_name, apply_first_digit,
                                                    minimum_sampe=minimum_sampe)
            if resp_digit_count is not None and total_digit_count is not None:
                # _, p_value = chisquare(total_digit_count, resp_digit_count)
                # score = p_value < 0.05
                score = jensen_shannon_distance(np.array(total_digit_count), np.array(resp_digit_count))
            results.append((resp, var, score))
    return pd.DataFrame(results, columns=[responsible_col, 'variable_name', feature_name])


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
    if min_value <= 0:
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


def filter_variables_by_magnitude(df, feature_name, variables, min_order_of_magnitude=3):
    # Define a function to calculate order of magnitude
    def order_of_magnitude(num):
        if num == 0:
            return 0
        elif num < 0:
            num = -num
        return int(math.floor(math.log10(num)))

    # Find columns that span at least min_order_of_magnitude
    valid_variables = []
    for var in variables:
        var_values = df[df['variable_name'] == var][feature_name]  # Remove NaNs to avoid issues
        max_magnitude = order_of_magnitude(var_values.max())
        min_magnitude = order_of_magnitude(var_values.min())

        if max_magnitude - min_magnitude >= min_order_of_magnitude:
            valid_variables.append(var)

    return valid_variables


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


def calculate_entropy(column, unique_values, min_record_sample=10):
    """
    Calculate the normalized entropy of a given column.

    Parameters:
    - column (pd.Series): The column for which the entropy is calculated.
    - unique_values (int): The number of unique values in the column.
    - min_record_sample (int, optional): The minimum sample size required
      relative to the number of unique values. Defaults to 10.

    Returns:
    - float or None: Returns normalized entropy if conditions are met,
      0 for single value distributions with enough samples,
      otherwise None.
    """

    # Compute the probability distribution of unique values in the column
    # This uses value counts and then normalizes the counts to get probabilities
    prob_distribution = column.value_counts(normalize=True)

    # Check conditions to calculate normalized entropy:
    # 1. There should be more than one unique value
    # 2. The number of records should be above a certain threshold
    #    based on the number of unique values
    if unique_values > 1 and column.shape[0] >= min_record_sample * unique_values:
        entropy_ = entropy(prob_distribution.values) / np.log2(unique_values)
    # Check conditions where entropy is 0:
    # 1. Only one unique value is present in the distribution
    # 2. The number of records meets the required threshold
    elif unique_values == 1 and column.shape[0] >= min_record_sample * unique_values:
        entropy_ = 0
    # If none of the above conditions are met, return None
    else:
        entropy_ = None

    return entropy_


def adjustable_winsorize(data, initial_lower=0.05, initial_upper=0.05, step=0.01):
    lower_limit = initial_lower
    upper_limit = initial_upper
    winsorized_data = winsorize(data, limits=[lower_limit, upper_limit])

    while len(np.unique(winsorized_data)) <= 1 and (lower_limit > 0 or upper_limit > 0):
        lower_limit = max(0, lower_limit - step)
        upper_limit = max(0, upper_limit - step)
        winsorized_data = winsorize(data, limits=[lower_limit, upper_limit])

    return winsorized_data
