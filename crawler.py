import yaml
from logging import Logger
from typing import Dict, Any


class Crawler:

    def __init__(self):
        pass

    def load_configuration(self, config_file: str):
        raise NotImplementedError

    def worker_routine(self, task: Any, shared_argv: Dict[str, Any], private_argv: Dict[str, Any], logger: Logger, save_queue=None):
        raise NotImplementedError

    def load_save_configuration(self, config_file: str):
        with open(config_file, "r") as file:
            data_dict = yaml.safe_load(file)
            save_id = data_dict["save_id"]
            save_dir = data_dict["save_dir"]
            return save_id, save_dir
