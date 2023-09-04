import json
import pandas as pd
import numpy as np
import os
import shutil
import zipfile
from src.utils.general_utils import *


def load_dataframes(processed_data_path):
    df_paradata = pd.read_pickle(os.path.join(processed_data_path, 'paradata.pkl'))
    df_microdata = pd.read_pickle(os.path.join(processed_data_path, 'microdata.pkl'))
    df_questionnaire = pd.read_pickle(os.path.join(processed_data_path, 'questionnaire.pkl'))

    # df_paradata = pd.read_csv(os.path.join(processed_data_path, 'paradata.csv'))
    # df_microdata = pd.read_csv(os.path.join(processed_data_path, 'microdata.csv'))
    # df_questionnaire = pd.read_csv(os.path.join(processed_data_path, 'questionnaire.csv'))

    # paradata_dtypes = pd.read_pickle(os.path.join(processed_data_path, 'df_paradata_dtypes.pkl'))
    # df_paradata = assign_type(df_paradata, paradata_dtypes)
    #
    # microdata_dtypes = pd.read_pickle(os.path.join(processed_data_path, 'df_microdata_dtypes.pkl'))
    # df_microdata = assign_type(df_microdata, microdata_dtypes)
    #
    # questionnaire_dtypes = pd.read_pickle(os.path.join(processed_data_path, 'df_questionnaires_dtypes.pkl'))
    # df_questionnaire = assign_type(df_questionnaire, questionnaire_dtypes)

    return df_paradata, df_questionnaire, df_microdata


def save_dataframes(df_paradata, df_questionnaires, df_microdata, processed_data_path):
    if not os.path.exists(processed_data_path):
        os.makedirs(processed_data_path)
    df_paradata.to_pickle(os.path.join(processed_data_path, 'paradata.pkl'))
    # # Save Questionaire
    df_questionnaires.to_pickle(os.path.join(processed_data_path, 'questionnaire.pkl'))
    # # Save Microdata dtypes
    df_microdata.to_pickle(os.path.join(processed_data_path, 'microdata.pkl'))

    # # Save Paradata csv
    # df_paradata.to_csv(os.path.join(processed_data_path, 'paradata.csv'), index=False)
    # # Save Questionaire
    # df_questionnaires.to_csv(os.path.join(processed_data_path, 'questionnaire.csv'), index=False)
    # # Save Microdata dtypes
    # df_microdata.to_csv(os.path.join(processed_data_path, 'microdata.csv'), index=False)

    # # Save Paradata dtypes
    # df_paradata.dtypes.to_pickle(os.path.join(processed_data_path, 'df_paradata_dtypes.pkl'))
    # # Save Questionaire dtypes
    # df_questionnaires.dtypes.to_pickle(os.path.join(processed_data_path, 'df_questionnaires_dtypes.pkl'))
    # # Save Paradata dtypes
    # df_microdata.dtypes.to_pickle(os.path.join(processed_data_path, 'df_microdata_dtypes.pkl'))


def get_data(survey_path, survey_name, survey_version):
    """
    This function wraps up the entire process of data extraction from the survey files.
    It calls the get_questionaire, get_paradata, and get_microdata functions in sequence,
    each one with its corresponding arguments.

    Parameters:
    survey_path (str): The directory path where the survey files are located.

    Returns:
    df_paradata (DataFrame): The DataFrame containing all the paradata.
    df_questionnaires (DataFrame): DataFrame containing information about the questionnaire used for the survey.
    df_microdata (DataFrame): The DataFrame containing all the microdata (survey responses).
    """
    df_questionnaires = get_questionaire(survey_path, survey_name, survey_version)
    df_paradata = get_paradata(survey_path, df_questionnaires, survey_name, survey_version)
    df_microdata = get_microdata(survey_path, df_questionnaires, survey_name, survey_version)

    return df_paradata, df_questionnaires, df_microdata


def transform_multi(df, variable_list, transformation_type):
    """
    This function takes a DataFrame and a list of variable names and applies a transformation depending on
    transformation_type to the variables in the DataFrame that start with the given variable names.

    The transformation can be either 'unlinked,' 'linked,' 'list,' or 'gps.'

    Parameters:
    df (DataFrame): The DataFrame to be transformed.
    variable_list (list): The list of variable names to be transformed.
    transformation_type (str): The type of transformation to apply. Must be 'unlinked,' 'linked,' 'list,' or 'gps.'

    Returns:
    DataFrame: The transformed DataFrame.

    Raises:
    ValueError: If transformation_type is not 'unlinked,' 'linked,' 'list,' or 'gps.'
    """
    if transformation_type not in ['unlinked', 'linked', 'list', 'gps']:
        raise ValueError("transformation_type must be either 'unlinked', 'linked', 'list', or 'gps'")

    transformed_df = pd.DataFrame(index=df.index)  # DataFrame for storing transformations

    for var in variable_list:
        if var in df.columns:
            # Drop the target column, should it exist (only text list question on a linked roster)
            df = df.drop(var, axis=1)

        related_cols = [col for col in df.columns if col.startswith(f"{var}__")]

        if related_cols:
            transformation = [[] for _ in range(len(df))] \
                if transformation_type != 'gps' \
                else ['' for _ in range(len(df))]

            for col in related_cols:

                if transformation_type == 'unlinked':
                    suffix = int(col.split('__')[1])
                    mask = df[col] > 0
                    transformation = [x + [suffix] if mask.iloc[i] else x for i, x in enumerate(transformation)]
                elif transformation_type == 'linked':
                    # !TODO if you add the (df[col] != -999999999) filter it removes also list that not only contains -999...
                    mask = (df[col].notna())  # & (df[col] != -999999999)
                    transformation = [x + [df.at[i, col]] if mask.iloc[i] else x for i, x in enumerate(transformation)]
                elif transformation_type == 'list':
                    mask = (df[col] != '##N/A##') & (df[col] != '')
                    transformation = [x + [df.at[i, col]] if mask.iloc[i] else x for i, x in enumerate(transformation)]
                elif transformation_type == 'gps':
                    transformation = [x + (',' if x else '') + (str(df.at[i, col])
                                                                if pd.notna(df.at[i, col])
                                                                   and df.at[i, col] not in ['##N/A##', -999999999]
                                                                else '') for i, x in enumerate(transformation)]

            def remove_unset_value(sub_list):
                sub = list(filter(lambda v: v not in [-999999999, '##N/A##'], sub_list))
                sub = [ele if ele != [] else '##N/A##' for ele in sub]
                sub = sub if sub != [] and list(set(sub)) != ['##N/A##'] else '##N/A##'
                return sub

            transformation = [remove_unset_value(x)
                              if x else float('nan') for x in transformation] if transformation_type != 'gps' else [
                x if x else '' for x in transformation]
            transformed_df[var] = transformation  # Add the transformation to the transformed DataFrame
            df = df.drop(related_cols, axis=1)  # Drop the original columns

    df = pd.concat([df, transformed_df], axis=1)  # Concatenate the original DataFrame with the transformations

    return df.copy()


def get_microdata(survey_path, df_questionnaires, survey_name, survey_version):
    """
    This function loads microdata from .dta files in the specified directory and reshapes it into a long format. It also
    applies a number of transformations to handle multi-options, list, and GPS coordinates questions.

    Parameters:
    survey_path (str): The directory path where the survey .dta files are located.
    df_questionnaires (DataFrame): DataFrame containing information about the questionnaire used for the survey.

    Returns:
    combined_df (DataFrame): The combined and processed DataFrame containing all survey responses.
    """

    # List of variables to exclude
    drop_list = ['interview__key', 'sssys_irnd', 'has__errors', 'interview__status', 'assignment__id']

    file_names = [file for file in os.listdir(survey_path) if
                  (file.endswith('.dta') or file.endswith('.tab')) and not file.startswith(
                      ('interview__', 'assignment__', 'paradata.tab'))]

    # define multi/list question conditions
    unlinked_mask = (df_questionnaires['type'] == 'MultyOptionsQuestion') & (df_questionnaires['is_linked'] == False)
    linked_mask = (df_questionnaires['type'] == 'MultyOptionsQuestion') & (df_questionnaires['is_linked'] == True)
    list_mask = (df_questionnaires['type'] == 'TextListQuestion')
    gps_mask = (df_questionnaires['type'] == 'GpsCoordinateQuestion')

    # extract multi/list question lists from conditions
    multi_unlinked_vars = df_questionnaires.loc[unlinked_mask, 'variable_name'].tolist()
    multi_linked_vars = df_questionnaires.loc[linked_mask, 'variable_name'].tolist()
    list_vars = df_questionnaires.loc[list_mask, 'variable_name'].tolist()
    gps_vars = df_questionnaires.loc[gps_mask, 'variable_name'].tolist()

    # Iterate over each file
    all_dfs = []
    for file_name in file_names:

        if file_name.endswith('.dta'):
            df = pd.read_stata(os.path.join(survey_path, file_name), convert_categoricals=False, convert_missing=True)
            df = df.where(df.astype(str) != '.a', -999999999)  # replace '.a' with -999999999 to match tabular export
            df = df.where(df.astype(str) != '.', np.nan)  # replace '.' with np.nan

        else:
            df = pd.read_csv(os.path.join(survey_path, file_name), sep='\t')

        # drop system-generated columns
        df.drop(columns=[col for col in drop_list if col in df.columns], inplace=True)

        # transform multi/list questions
        df = transform_multi(df, multi_unlinked_vars, 'unlinked')
        df = transform_multi(df, multi_linked_vars, 'linked')
        df = transform_multi(df, list_vars, 'list')
        df = transform_multi(df, gps_vars, 'gps')

        # create roster_level from __id columns if on roster level, else '' if main questionnaire file
        roster_ids = [col for col in df.columns if col.endswith("__id") and col != "interview__id"]
        if roster_ids:
            df['roster_level'] = df[roster_ids].apply(lambda row: ",".join(map(str, row)), axis=1)
            df.drop(columns=roster_ids, inplace=True)
        else:
            df['roster_level'] = ''

        id_vars = ['interview__id', 'roster_level']
        value_vars = [col for col in df.columns if col not in id_vars]
        df_long = df.melt(id_vars=id_vars, value_vars=value_vars, var_name='variable', value_name='value')
        df_long['filename'] = file_name

        all_dfs.append(df_long)
    if len(all_dfs) > 0:

        combined_df = pd.concat(all_dfs, ignore_index=True)
    else:
        combined_df = pd.DataFrame()

    # Drop column with null or empty string in value
    # Function to check if the value is not an empty string or NaN
    def is_valid(value):
        if isinstance(value, list):
            return True  # bool(value)  # Not an empty list
        return value != '' and pd.notna(value)  # Not an empty string or NaN

    # Keep rows where the 'value' column passes the is_valid check
    combined_df = combined_df[combined_df['value'].apply(is_valid)]

    combined_df = set_survey_name_version(combined_df, survey_name, survey_version)
    # Manage the case questionnaires are not available for the survey
    if df_questionnaires.empty is False:
        roster_columns = [c for c in combined_df.columns if '__id' in c and c != 'interview__id']
        combined_df = combined_df.merge(df_questionnaires, how='left',
                                        left_on=['variable', 'survey_name', 'survey_version'],
                                        right_on=['variable_name', 'survey_name', 'survey_version']).sort_values(
            ['interview__id', 'qnr_seq'] + roster_columns)

    combined_df.reset_index(drop=True, inplace=True)

    # Normalize columns
    combined_df.columns = [normalize_column_name(c) for c in combined_df.columns]
    return combined_df


def process_json_structure(children, parent_group_title, counter, question_data):
    """
    This function processes the JSON structure of a questionnaire, collecting information about the questions.

    Parameters:
    children (list): The children nodes in the current JSON structure.
    parent_group_title (str): The title of the parent group for the current child nodes.
    counter (int): A counter to keep track of the sequence of questions.
    question_data (list): A list where data about each question is appended as a dictionary.

    Returns:
    counter (int): The updated counter value after processing all children nodes.

    """
    for child in children:
        if "$type" in child:
            question_data.append({
                "qnr_seq": counter,
                "VariableName": child.get("VariableName"),
                "type": child["$type"],
                "QuestionType": child.get("QuestionType"),
                "Answers": child.get("Answers"),
                "Children": child.get("Children"),
                "ConditionExpression": child.get("ConditionExpression"),
                "HideIfDisabled": child.get("HideIfDisabled"),
                "Featured": child.get("Featured"),
                "Instructions": child.get("Instructions"),
                "Properties": child.get("Properties"),
                "PublicKey": child.get("PublicKey"),
                "QuestionScope": child.get("QuestionScope"),
                "QuestionText": child.get("QuestionText"),
                "StataExportCaption": child.get("StataExportCaption"),
                "VariableLabel": child.get("VariableLabel"),
                "IsTimestamp": child.get("IsTimestamp"),
                "ValidationConditions": child.get("ValidationConditions"),
                "YesNoView": child.get("YesNoView"),
                "IsFilteredCombobox": child.get("IsFilteredCombobox"),
                "IsInteger": child.get("IsInteger"),
                "CategoriesId": child.get("CategoriesId"),
                "Title": child.get("Title"),
                "IsRoster": child.get("IsRoster"),
                "LinkedToRosterId": child.get("LinkedToRosterId"),
                "LinkedToQuestionId": child.get("LinkedToQuestionId"),
                "CascadeFromQuestionId": child.get("CascadeFromQuestionId"),
                "parents": parent_group_title
            })
            counter += 1

        if "Children" in child:
            child_group_title = child.get("Title", "")
            counter = process_json_structure(child["Children"], parent_group_title + " > " + child_group_title, counter,
                                             question_data)

    return counter


def get_categories(directory):
    """
    This function retrieves categories from Excel files within a directory.

    Parameters:
    directory (str): The directory where the category Excel files are stored.

    Returns:
    dict: A dictionary containing category data. Each key represents a filename, and each value is another dictionary
    containing 'n_answers' and 'answer_sequence' which represents the number of answers and the sequence of the answer IDs
    respectively.

    """
    categories = {}
    files = [f for f in os.listdir(directory) if f.endswith('.xlsx') or f.endswith('.xls')]
    for file in files:
        file_path = os.path.join(directory, file)
        df = pd.read_excel(file_path)
        n_answers = df.shape[0]
        answer_sequence = df['id'].tolist()
        categories[file] = {'n_answers': n_answers, 'answer_sequence': answer_sequence}
    return categories


def update_df_categories(row, categories):
    """
    This function updates a DataFrame row with categories information if applicable.

    Parameters:
    row (Series): The Questioner DataFrame row to be updated.
    categories (dict): A dictionary containing categories data, keys are 'CategoriesId'.

    Returns:
    Series: The updated DataFrame row.

    """
    if row['CategoriesId'] in categories:
        row['n_answers'] = categories[row['CategoriesId']]['n_answers']
        row['answer_sequence'] = categories[row['CategoriesId']]['answer_sequence']
    return row


def get_questionaire(survey_path, survey_name, survey_version):
    """
    This function loads and processes a questionnaire from a JSON file located at the specified path.
    It also handles the categorization of the data.

    Parameters:
    survey_path (str): The path to the directory containing the questionnaire and categories data.

    Returns:
    qnr_df (DataFrame): A processed DataFrame containing the questionnaire data.

    """
    qnr_df = pd.DataFrame()
    questionaire_path = os.path.join(survey_path, 'Questionnaire/content/document.json')
    if os.path.exists(questionaire_path):
        with open(questionaire_path, encoding='utf8') as file:
            json_data = json.load(file)

        question_data = []
        question_counter = 0

        process_json_structure(json_data["Children"], "", question_counter, question_data)

        qnr_df = pd.DataFrame(question_data)
        qnr_df['answer_sequence'] = qnr_df['Answers'].apply(
            lambda x: [int(item['AnswerValue']) for item in x] if x else np.nan)
        qnr_df['n_answers'] = qnr_df['Answers'].apply(lambda x: len(x) if x else np.nan)
        qnr_df['is_linked'] = (qnr_df['LinkedToRosterId'].notna()) | (qnr_df['LinkedToQuestionId'].notna())
        qnr_df['parents'] = qnr_df['parents'].str.lstrip(' > ')
        split_columns = qnr_df['parents'].str.split(' > ', expand=True)
        split_columns.columns = [f"parent_{i + 1}" for i in range(split_columns.shape[1])]
        qnr_df = pd.concat([qnr_df, split_columns], axis=1)
        qmask = qnr_df['QuestionScope'] == 0
        qnr_df['question_sequence'] = qmask.cumsum()
        qnr_df.loc[~qmask, 'question_sequence'] = None
    categories_path = os.path.join(survey_path, 'Questionnaire/content/Categories')
    if os.path.exists(categories_path):
        categories = get_categories(categories_path)

        qnr_df = qnr_df.apply(lambda row: update_df_categories(row, categories), axis=1)

    qnr_df.reset_index(drop=True, inplace=True)
    # Normalize columns
    qnr_df.columns = [normalize_column_name(c) for c in qnr_df.columns]
    qnr_df = set_survey_name_version(qnr_df, survey_name, survey_version)
    return qnr_df


def get_paradata(survey_path, df_questionnaires, survey_name, survey_version):
    """
    This function loads and processes a paradata file from the provided path and merges it with the questionnaire dataframe.
    The function also generates a date-time column from the timestamp and marks whether the answer has changed.

    Parameters:
    para_path (str): A string path to the paradata .csv file.
    df_questionnaires (DataFrame): A Pandas DataFrame containing the questionnaire data.

    Returns:
    df_para (DataFrame): A processed DataFrame containing the merged data from the paradata file and the questionnaire DataFrame.

    """
    para_path = os.path.join(survey_path, 'paradata.tab')
    df_para = pd.read_csv(para_path, delimiter='\t')

    # split the parameter column, first from the left, then from the right to avoid potential data entry issues
    df_para[['param', 'answer']] = df_para['parameters'].str.split('\|\|', n=1, expand=True)
    df_para[['answer', 'roster_level']] = df_para['answer'].str.rsplit('||', n=1, expand=True)

    #    df_para['roster_level'] = df_para['roster_level'].str.replace("|","")  # if yes/no questions are answered with yes for the first time, "|" will appear in roster

    df_para['timestamp_utc'] = pd.to_datetime(df_para['timestamp_utc'])  # generate date-time, TZ not yet considered

    df_para['tz_offset'] = pd.to_timedelta(df_para['tz_offset'].str.replace(':', ' hours ') + ' minutes')

    # Adjust the date column by the timezone offset
    df_para['timestamp_local'] = df_para['timestamp_utc'] + df_para['tz_offset']

    df_para = set_survey_name_version(df_para, survey_name, survey_version)

    if df_questionnaires.empty is False:
        q_columns = ['qnr_seq', 'variable_name', 'type', 'question_type', 'answers', 'question_scope',
                     'yes_no_view', 'is_filtered_combobox',
                     'is_integer', 'cascade_from_question_id', 'answer_sequence', 'n_answers', 'question_sequence',
                     'survey_name', 'survey_version']
        df_para = df_para.merge(df_questionnaires[q_columns], how='left',
                                left_on=['param', 'survey_name', 'survey_version'],
                                right_on=['variable_name', 'survey_name', 'survey_version'])

    # Normalize column names
    df_para.columns = [normalize_column_name(c) for c in df_para.columns]
    return df_para


def set_survey_name_version(df, survey_name, survey_version):
    """
    This function adds the survey_name and survey_version as new columns to each DataFrame in the list of DataFrames.

    Parameters:
    dfs (dataframe): DataFrames to which the survey_name and survey_version are to be added as new columns.
    survey_name (str): The name of the survey to be added as a new column in each DataFrame.
    survey_version (str): The version of the survey to be added as a new column in each DataFrame.

    Returns:
    df (list): The updated DataFrame, each containing new columns for the survey_name and survey_version.
    """
    df['survey_name'] = survey_name
    df['survey_version'] = survey_version
    return df


class ImportManager:
    """
    This class manages the different paths defined in the configuration file.

    Attributes:
    config: The configuration settings.
    file_dict: A dictionary that maps survey names to their respective files.

    Methods:
    get_files(): Creates a dictionary of zip files from the surveys defined in config.
    get_survey_version(): Filters the file dictionary based on the surveys specified in the config.
    extract(overwrite_dir): Extracts the contents of the zip files to a target directory.
    get_dataframes(save_to_disk, reload): Returns dataframes of the paradata, questionnaires, and microdata.
    """

    def __init__(self, config):
        """
        The constructor for the ImportManager class.

        Parameters:
        config: The configuration settings.
        """
        # Extract attributes
        self.config = config
        self.file_dict = {}
        self.get_survey_version()


    def get_files(self):
        """
        Get a dictionary with all zip files from the surveys defined in the config.
        """
        # Get a dictionary with all zip files from the surveys defined in config
        if self.config.surveys == 'all':
            import_path = os.listdir(self.config['environment']['data']['externals'])
        else:
            # Get surveys defined in the config file that are present in the path
            import_path = [survey for survey in self.config.surveys if survey in os.listdir(self.config['environment']['data']['externals'])]
        if len(import_path) == 0:
            raise ValueError(f"ERROR: survey path {self.config['export_path']} does not exists")
        for survey_name in import_path:
            if os.path.isdir(os.path.join(self.config['environment']['data']['externals'], survey_name)):
                self.file_dict[survey_name] = self.file_dict.get(survey_name, {})

                survey_path = os.path.join(self.config['environment']['data']['externals'], survey_name)
                for filename in os.listdir(survey_path):
                    if filename.endswith('.zip'):

                        try:
                            questionnaire, version, file_format, interview_status = get_file_parts(filename)
                            q_name = f"{questionnaire}_{str(version)}"
                            self.file_dict[survey_name][q_name] = self.file_dict[survey_name].get(q_name, {
                                'file_path': survey_path})
                            self.file_dict[survey_name][q_name][file_format] = filename
                        except ValueError:
                            print(f"WARNING: Survey {survey_name} with version filename {filename} Skipped")
        # Filter out folders without ZIP files.
        self.file_dict = {k: v for k, v in self.file_dict.items() if len(v) > 0}

    def get_survey_version(self):
        """
        Filters the file dictionary based on the surveys specified in the config.
        """
        self.get_files()
        if self.config.surveys != 'all':
            if self.config.survey_version is None:
                if len(self.file_dict[self.config.surveys[0]]) > 1:
                    raise ValueError(f"There are multiple versions in {self.config['export_path']}. "
                                     f"Either specify survey_version=all in python main.py i.e. \n"
                                     f"python main.py export_path={self.config['export_path']} output_file={self.config['output_file']} survey_version=all "
                                     f"\n OR provide a path with only one version.")
            elif self.config.survey_version == 'all':
                self.file_dict = {survey: survey_data for survey, survey_data in self.file_dict.items() if
                                  survey in self.config.surveys}
            else:
                self.file_dict = {k: {nk: v for nk, v in nested_dict.items() if nk in self.config.survey_version} for
                                  k, nested_dict in self.file_dict.items() if k in self.config.surveys}

    def extract(self, overwrite_dir=False):
        """
        Extracts the contents of the zip files to a target directory.

        Parameters:
        overwrite_dir: A boolean indicating whether to overwrite the existing directory.
        """
        if self.config['environment']['extract']:
            for survey_name, survey in self.file_dict.items():
                target_dir = os.path.join(self.config['environment']['data']['raw'], survey_name)
                if overwrite_dir and os.path.exists(target_dir):
                    shutil.rmtree(target_dir)
                # Create a new target directory if it does not yet exist
                if not os.path.exists(target_dir):
                    os.makedirs(target_dir)

                # By default, delete target directory if already exist
                for survey_version, files in survey.items():
                    file_path = files['file_path']
                    dest_path = os.path.join(target_dir, survey_version)
                    if overwrite_dir and os.path.exists(dest_path):
                        shutil.rmtree(dest_path)

                    # Create a new target directory if it does not yet exist
                    if not os.path.exists(dest_path):
                        os.makedirs(dest_path)

                    # Extract the contents of the main zip file
                    paradata_file = files.get('Paradata')
                    if paradata_file:
                        try:
                            paradata_path = os.path.join(file_path, paradata_file)
                            with zipfile.ZipFile(paradata_path, 'r') as zip_ref:
                                zip_ref.extractall(dest_path)
                        except ValueError:
                            print(f"WARNING: survey {survey_name} with version {survey_version} has not paradata file")
                            shutil.rmtree(dest_path)
                    # If microdata
                    if files.get('Tabular'):
                        try:
                            microdata_file = os.path.join(file_path, files['Tabular'])
                            with zipfile.ZipFile(microdata_file, 'r') as zip_ref:
                                zip_ref.extractall(dest_path)
                            content_zip_path = os.path.join(dest_path, "Questionnaire", "content.zip")
                            content_dir = os.path.join(dest_path, "Questionnaire", "content")
                            with zipfile.ZipFile(content_zip_path, 'r') as zip_ref:
                                zip_ref.extractall(content_dir)
                        except ValueError:
                            print(f"WARNING: survey {survey_name} with version {survey_version} has missing files")
                            shutil.rmtree(dest_path)

    def get_dataframes(self, save_to_disk=True, reload=False):
        """
        Returns dataframes of the paradata, questionnaires, and microdata.

        Parameters:
        save_to_disk: A boolean indicating whether to save the dataframes to disk.
        reload: A boolean indicating whether to reload the data.

        Returns:
        df_paradata, df_questionnaires, df_microdata: Dataframes containing the paradata, questionnaires, and microdata from the different surveys defined in the config.
        """
        # code omitted for brevity
        dfs_paradata = []
        dfs_questionnaires = []
        dfs_microdata = []
        for survey_name, survey in self.file_dict.items():
            target_dir = os.path.join(self.config['environment']['data']['raw'], survey_name)

            for survey_version, files in survey.items():
                print(f"IMPORTING: {survey_name} with version {survey_version}. ")
                survey_path = os.path.join(target_dir, survey_version)
                processed_data_path = os.path.join(survey_path, 'processed_data')
                if reload is False and os.path.isdir(processed_data_path):
                    df_paradata, df_questionnaires, df_microdata = load_dataframes(processed_data_path)
                else:
                    df_paradata, df_questionnaires, df_microdata = get_data(survey_path, survey_name, survey_version)
                    if save_to_disk:
                        save_dataframes(df_paradata, df_questionnaires, df_microdata, processed_data_path)
                print(f"{survey_name} with version {survey_version} loaded. "
                      f"\n"
                      f"Paradata shape: {df_paradata.shape} "
                      f"Questionnaires shape: {df_questionnaires.shape} "
                      f"Microdata shape: {df_microdata.shape} "
                      )
                dfs_paradata.append(df_paradata)
                dfs_questionnaires.append(df_questionnaires)
                dfs_microdata.append(df_microdata)

        # create unique dataframe with all surveys
        dfs_paradata = pd.concat(dfs_paradata)
        dfs_questionnaires = pd.concat(dfs_questionnaires)
        dfs_microdata = pd.concat(dfs_microdata)

        dfs_paradata.reset_index(drop=True, inplace=True)
        dfs_questionnaires.reset_index(drop=True, inplace=True)
        dfs_microdata.reset_index(drop=True, inplace=True)

        return dfs_paradata, dfs_questionnaires, dfs_microdata
