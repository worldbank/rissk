import os
from omegaconf import DictConfig, OmegaConf
from hydra.core.hydra_config import HydraConfig
from src.unit_proccessing import *
import hydra
# from memory_profiler import memory_usage
import warnings

warnings.simplefilter(action='ignore', category=Warning)


def manage_path(config):
    if config['export_path'] is not None:
        if os.path.isabs(config['export_path']) is False:
            root_path = HydraConfig.get().runtime.cwd
            config['export_path'] = os.path.join(root_path, config['export_path'])
        config['environment']['data']['externals'] = os.path.dirname(config['export_path'])
        config['surveys'] = [os.path.basename(config['export_path'])]
    if os.path.isabs(config['output_file']) is False:
        root_path = HydraConfig.get().runtime.cwd
        config['output_file'] = os.path.join(root_path, config['output_file'])
    return config


@hydra.main(config_path='configuration', version_base='1.1', config_name='main.yaml')
def unit_risk_score(config: DictConfig) -> None:
    # print(OmegaConf.to_yaml(config))
    print("*" * 12)
    config = manage_path(config)
    try:
        survey_class = UnitDataProcessing(config)
        df_item = survey_class.df_item
        df_unit = survey_class.df_unit
        survey_class.make_global_score()
        survey_class.save()
    except ValueError as e:
        print(f"An error occurred: {e}")


if __name__ == "__main__":
    unit_risk_score()
    # mem_usage = memory_usage(unit_risk_score)
    # print(f"Memory usage (in MB): {max(mem_usage)}")
