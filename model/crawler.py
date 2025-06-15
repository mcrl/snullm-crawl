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
