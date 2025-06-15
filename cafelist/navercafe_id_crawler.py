from typing import List
from model.crawler import Crawler
import yaml
from util.env import get_iplist
from util.argcheck import parse_iplist
from util.argcheck import parse_iplist

from cafelist.navercafe_id_handler import handle_cafe_id


class navercafeIDCrawler(Crawler):
    def __init__(self, **kwargs):
        super(navercafeIDCrawler, self).__init__()
        self.save_id = "navercafe_id"
        self.save_dir = "data/navercafe_id"

    def load_configuration(self, config_file: str):
        with open(config_file, "r") as file:
            data_dict = yaml.safe_load(file)

        ips = data_dict["ips"]
        default_interval = data_dict.get("default_interval", 1)
        if ips is not None:
            ips, intervals = parse_iplist(
                ips, default_interval=default_interval)

        if ips is None or len(ips) == 0:
            ips = get_iplist()
            intervals = [default_interval] * len(ips)

        max_page = data_dict.get("max_page", 10)
        private_args = []
        for ip, interval in zip(ips, intervals):
            argv = {"ip": ip, "interval": interval}
            private_args.append(argv)
        shared_argv = {"max_page": max_page}
        tasks = [(i, len(ips)) for i in range(len(ips))]
        return tasks, shared_argv, private_args

    def worker_routine(self, *args, **kwargs):
        handle_cafe_id(*args, **kwargs)
