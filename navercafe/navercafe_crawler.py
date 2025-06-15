from typing import List
from model.crawler import Crawler
import yaml
import os

from util.env import get_iplist
from util.argcheck import parse_iplist
from navercafe.handler import handle_cafe
from navercafe.checker import is_processed
from navercafe.structs import Cafe
from util.fileutil import read_tsv
from util.argcheck import parse_iplist


class navercafeCrawler(Crawler):
    def __init__(self, **kwargs):
        super(navercafeCrawler, self).__init__()
        self.save_id = "navercafe"
        self.save_dir = "data/navercafe_merged"

    def _build_cafelist(self, cafelist_path: str) -> List[Cafe]:
        cids = read_tsv(cafelist_path, header=True)
        cids = [cid[0] for cid in cids]
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
