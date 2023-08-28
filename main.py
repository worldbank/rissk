import os

from omegaconf import DictConfig, OmegaConf
from src.unit_proccessing import *
import hydra
#from memory_profiler import memory_usage


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


def manage_survey_path(config):
    if config.survey_path is not None:
        config.data.externals = os.path.dirname(config.survey_path)
        config.surveys = [os.path.basename(config.survey_path)]
    return config


@hydra.main(config_path='configuration', version_base='1.1', config_name='main.yaml')
def unit_risk_score(config: DictConfig) -> None:
    #print(OmegaConf.to_yaml(config))
    print("*" * 12)
    config = manage_survey_path(config)
    config = manage_relative_path(config, hydra.utils.get_original_cwd())
    config = manage_survey_definition(config)
    features_class = UnitDataProcessing(config)
    df_item = features_class.df_item
    df_unit = features_class.df_unit
    features_class.make_global_score()
    features_class.save()


if __name__ == "__main__":
    unit_risk_score()
    #mem_usage = memory_usage(unit_risk_score)
    #print(f"Memory usage (in MB): {max(mem_usage)}")
