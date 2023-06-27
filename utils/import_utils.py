import os
import hydra
import json
from omegaconf import DictConfig
import pandas as pd
from hydra import initialize, initialize_config_module, initialize_config_dir, compose
from omegaconf import OmegaConf


def get_data(config):
    paradata = {}
    questionnaires = {}
    microdata = {}
    if config.dataset == 'all':
        for survey_name in os.listdir(config.data.externals):
            survey_path = os.path.join(config.data.externals, survey_name)
            questionnaires[survey_name] = get_questionaire(os.path.join(survey_path, 'document.json'))
            paradata[survey_name] = get_paradata(os.path.join(survey_path, 'paradata.tab'), questionnaires[survey_name])
    else:
        survey_name = config.dataset
        survey_path = os.path.join(config.data.externals, survey_name)
        questionnaires[survey_name] = get_questionaire(os.path.join(survey_path, 'document.json'))
        paradata[survey_name] = get_paradata(os.path.join(survey_path, 'paradata.tab'), questionnaires[survey_name])

    return paradata, questionnaires, microdata


def process_json_structure(json_dict, type_mapping):

    for child in json_dict:
        if "$type" in child:
            variable_name = child.get("VariableName")

            type_value = child["$type"]
            if "YesNoView" in child:
                if child["YesNoView"]:
                    type_value = "YesNoQuestion"  # for yes/no questions, overwrite with custom question type

            if variable_name:
                type_mapping[variable_name] = type_value

        if "Children" in child:
            process_json_structure(child["Children"], type_mapping)
    return type_mapping


def get_questionaire(json_path):
    # create a mapping of VariableName to $type
    type_mapping = {}
    with open(json_path, 'r') as file:
        qnr_structure = json.load(file)
        process_json_structure(qnr_structure["Children"], type_mapping)
    return type_mapping


def get_paradata(para_path, type_mapping):
    df_para = pd.read_csv(para_path, delimiter='\t')
    df_para[['param', 'answer', 'roster_level']] = df_para['parameters'].str.split('\|\|', expand=True)  # split the parameter column
    df_para['datetime_utc'] = pd.to_datetime(df_para['timestamp_utc'])  # generate date-time, TZ not yet considered
    df_para['type'] = df_para['param'].map(type_mapping)
    df_para['answer_changed'] = False
    return df_para

