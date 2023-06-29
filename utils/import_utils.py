import os
import json
import pandas as pd
import os
import shutil
import zipfile
from hydra import initialize, initialize_config_module, initialize_config_dir, compose
from omegaconf import OmegaConf


def get_file_parts(filename):
    # Remove ".zip" and split by "_"
    filename_parts = filename[:-4].split("_")
    if len(filename_parts) < 4:
        print(f"ERROR: {filename} Not a valid Survey Solutions export file.")

    version, file_format, interview_status = filename_parts[-3:]
    try:
        version = int(version)
    except ValueError:
        print(f"ERROR: {filename} Not a valid Survey Solutions export file. Version not found.")
    questionnaire = "_".join(filename_parts[:-3])
    # Test input file has correct name
    if file_format not in ["Tabular", "STATA", "SPSS", "Paradata"]:
        print(f"ERROR: {filename} Not a valid Survey Solutions export file. Export type not found")

    if interview_status not in ["Approved", "InterviewerAssigned", "ApprovedBySupervisor", "ApprovedByHQ", "All"]:
        print(f"ERROR: {filename} Not a valid Survey Solutions export file. Interview status not found.")

    file_format = file_format if file_format == 'Paradata' else 'Tabular'
    return questionnaire, version, file_format, interview_status


class SurveyImport:
    def __init__(self, config):

        # Extract attributes
        self.config = config
        self.file_dict = {}
        self.get_survey_version()

    def get_files(self):
        # Get a dictionary with all zip files from the surveys defined in config
        if self.config.surveys == 'all':
            import_path = os.listdir(self.config.data.externals)
        else:
            # Get surveys defined in the config file that are present in the path
            import_path = [survey for survey in self.config.surveys if survey in os.listdir(self.config.data.externals)]
        for survey_name in import_path:
            if os.path.isdir(os.path.join(self.config.data.externals, survey_name)):
                self.file_dict[survey_name] = self.file_dict.get(survey_name, {})

                survey_path = os.path.join(self.config.data.externals, survey_name)
                for filename in os.listdir(survey_path):

                    if filename.endswith('.zip'):

                        try:
                            questionnaire, version, file_format, interview_status = get_file_parts(filename)
                            q_name = f"{questionnaire}_{str(version)}"
                            self.file_dict[survey_name][q_name] = self.file_dict[survey_name].get(q_name, {'file_path': survey_path})
                            self.file_dict[survey_name][q_name][file_format] = filename
                        except:
                            print(f"WARNING: Survey {survey_name} with version filename {filename} Skipped")
        # Filter out folders without ZIP files.
        self.file_dict = {k: v for k, v in self.file_dict.items() if len(v) > 0}

    def get_survey_version(self):
        self.get_files()
        if self.config.surveys != 'all':
            self.file_dict = {survey: survey_data for survey, survey_data in self.file_dict.items() if survey in self.config.surveys}

    def extract(self,  overwrite_dir=False):
        for survey_name, survey in self.file_dict.items():
            target_dir = os.path.join(self.config.data.raw, survey_name)
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
                    except:
                        pass
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
                    except:
                        pass

    def make_dataframes(self, save_to_disk=True, reload=True):
        survey_data_dict = {}
        for survey_name, survey in self.file_dict.items():
            target_dir = os.path.join(self.config.data.raw, survey_name)
            survey_data_dict[survey_name] = survey_data_dict.get(survey_name, {})
            for survey_version, files in survey.items():
                survey_path = os.path.join(target_dir, survey_version)
                processed_data_path = os.path.join(survey_path, 'processed_data')
                if reload is False and os.path.isdir(processed_data_path):
                    df_paradata, questionnaires, df_microdata = load_dataframes(processed_data_path)
                else:
                    df_paradata, questionnaires, df_microdata = get_data(survey_path)
                    if save_to_disk:
                        save_dataframes(df_paradata, questionnaires, df_microdata, processed_data_path)

                survey_data_dict[survey_name][survey_version] = {'paradata': df_paradata, 'questionnaire':questionnaires, 'microdata':df_microdata}
        return survey_data_dict



def load_dataframes(processed_data_path):

    df_paradata = pd.read_csv(os.path.join(processed_data_path,'paradata.csv'))
    df_microdata = pd.read_csv(os.path.join(processed_data_path,'microdata.csv'))
    json_path = os.path.join(processed_data_path,'questionnaire.json')
    with open(json_path, 'r') as file:
        questionnaires = json.load(file)
    return df_paradata, questionnaires, df_microdata


def save_dataframes(df_paradata, questionnaires, df_microdata, processed_data_path):
    if not os.path.exists(processed_data_path):
        os.makedirs(processed_data_path)

    df_paradata.to_csv(os.path.join(processed_data_path,'paradata.csv'), index = False)
    df_microdata.to_csv(os.path.join(processed_data_path,'microdata.csv'), index = False)
    json_path = os.path.join(processed_data_path,'questionnaire.json')
    with open(json_path,'w') as f:
        json.dump(questionnaires, f)
def get_data(survey_path):
    questionnaires = get_questionaire(survey_path)
    df_paradata = get_paradata(os.path.join(survey_path, 'paradata.tab'), questionnaires)
    df_microdata = get_miocrodata(survey_path, questionnaires)
    return df_paradata, questionnaires, df_microdata

def get_miocrodata(survey_path, question_mapping):
    # List of variables to exclude
    drop_list = ['interview__key', 'sssys_irnd', 'has__errors', 'interview__status', 'assignment__id']

    # List of file names
    file_names = [file for file in os.listdir(survey_path) if
                  file.endswith('.dta') and not file.startswith(('interview__', 'assignment__'))]
    # Iterate over each file
    all_dfs = []
    for file_name in file_names:
        df = pd.read_stata(os.path.join(survey_path, file_name), convert_categoricals=False)
        df.drop(columns=[col for col in drop_list if col in df.columns], inplace=True)
        id_vars = [col for col in df.columns if col.endswith("__id")]
        value_vars = [col for col in df.columns if col not in id_vars]
        df_long = df.melt(id_vars=id_vars, value_vars=value_vars, var_name='variable', value_name='value')
        df_long['filename'] = file_name
        all_dfs.append(df_long)

    combined_df = pd.concat(all_dfs, ignore_index=True)
    combined_df['type'], combined_df['question_scope'], combined_df['parent_group_title'] = zip(
        *combined_df['variable'].map(lambda x: question_mapping.get(x, ("Unknown", "Unknown", "Unknown")) if not pd.isnull(x) else ("Unknown", "Unknown", "Unknown")))
    return combined_df

def get_questionaire(survey_path):
    # create a mapping of VariableName to $type
    json_path = os.path.join(survey_path, 'Questionnaire/content/document.json')
    with open(json_path, 'r') as file:
        json_data = json.load(file)

        # Preprocess the JSON structure to create a mapping of VariableName to ($type, QuestionScope, ParentGroupTitle)
        question_mapping = {}


        def process_json_structure(children, parent_group_title):
            for child in children:
                if "$type" in child:
                    variable_name = child.get("VariableName")
                    type_value = child["$type"]
                    question_scope = child.get("QuestionScope")
                    question_mapping[variable_name] = (type_value, question_scope, parent_group_title)

                if "Children" in child:
                    child_group_title = child.get("Title", "")
                    process_json_structure(child["Children"], parent_group_title + " > " + child_group_title)

        process_json_structure(json_data["Children"], "")
    return question_mapping


def get_paradata(para_path, type_mapping):
    df_para = pd.read_csv(para_path, delimiter='\t')
    df_para[['param', 'answer', 'roster_level']] = df_para['parameters'].str.split('\|\|', expand=True)  # split the parameter column
    df_para['datetime_utc'] = pd.to_datetime(df_para['timestamp_utc'])  # generate date-time, TZ not yet considered
    df_para['type'] = df_para['param'].map(type_mapping)
    df_para['answer_changed'] = False
    return df_para

