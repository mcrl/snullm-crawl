from typing import List
import yaml

from daumcafe.checker import is_processed
from daumcafe.structs import Cafe
from util.fileutil import read_txt
from util.argcheck import parse_iplist


def build_cafelist(cafelist: str) -> List[Cafe]:
    cids = read_txt(cafelist, header=False)
    cafes = map(lambda cid: Cafe(cid), cids)
    return [cafe for cafe in cafes if not is_processed(cafe)]


def load_configuration(config_file: str):
    with open(config_file, "r") as file:
        data_dict = yaml.safe_load(file)

    ips = data_dict["ips"]
    default_interval = data_dict.get("default_interval", 1)
    ips, intervals = parse_iplist(ips, default_interval=default_interval)

    private_args = []
    for ip, interval in zip(ips, intervals):
        argv = {"ip": ip, "interval": interval}
        private_args.append(argv)
    shared_argv = {}

    cafelist_txt = data_dict["cafelist"]
    cafes = build_cafelist(cafelist_txt)

    return cafes, shared_argv, private_args
