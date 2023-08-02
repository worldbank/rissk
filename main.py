import os

from omegaconf import DictConfig, OmegaConf
from utils.process_utils import *
from utils.import_utils import *
from utils.score_process_utils import *
import hydra


def manage_relative_path(config, abosulute_path):
    for name, relative_path in config.data.items():
        if relative_path.startswith('../'):
            config['data'][name] = os.path.join(abosulute_path, relative_path.replace('../', ''))
    return config


def manage_survey_definition(config):
    if config['surveys'] != 'all' and type(config['surveys']) == str:
        config['surveys'] = [config['surveys']]
    if config['survey_version'] != 'all' and type(config['survey_version']) == str:
        config['survey_version'] = [config['survey_version']]
    return config


@hydra.main(config_path='configuration', version_base='1.1', config_name='main.yaml')
def unit_risk_score(config: DictConfig) -> None:
    #print(OmegaConf.to_yaml(config))
    print("*" * 12)
    config = manage_relative_path(config, hydra.utils.get_original_cwd())
    config = manage_survey_definition(config)
    survey_list = SurveyManager(config)
    survey_list.extract()
    dfs_paradata, dfs_questionnaires, dfs_microdata = survey_list.get_dataframes()
    features_class = FeatureDataProcessing(dfs_paradata, dfs_microdata, dfs_questionnaires, config)
    score_class = UnitScore(config, features_class)
    score_class.make_global_score()
    score_class.save()


if __name__ == "__main__":
    unit_risk_score()
