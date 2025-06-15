from typing import List
import yaml
from model.crawler import Crawler

from daumcafe.checker import is_processed
from daumcafe.structs import Cafe
from util.fileutil import read_txt
from util.argcheck import parse_iplist
from daumcafe.handler import handle_cafe
import os
from util.env import get_iplist


class daumcafeCrawler(Crawler):
    def __init__(self, **kwargs):
        super(daumcafeCrawler, self).__init__()
        self.save_id = "daumcafe"
        self.save_dir = "data/daumcafe_merged"

    def _build_cafelist(self, cafelist_path: str) -> List[Cafe]:
        script_dir = os.path.dirname(os.path.realpath(__file__))
        cafelist_path = os.path.join(script_dir, cafelist_path)
        cids = read_txt(cafelist_path, header=False)
        cafes = map(lambda cid: Cafe(cid), cids)
        return [cafe for cafe in cafes if not is_processed(cafe)]

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

        private_args = []
        for ip, interval in zip(ips, intervals):
            argv = {"ip": ip, "interval": interval}
            private_args.append(argv)
        shared_argv = {}

        cafelist_txt_path = data_dict["cafelist"]
        cafes = self._build_cafelist(cafelist_txt_path)

        return cafes, shared_argv, private_args

    def worker_routine(self, *args, **kwargs):
        handle_cafe(*args, **kwargs)
