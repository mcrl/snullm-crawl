from typing import List
import yaml

import multiprocessing as mp


from kin.structs import KinUser
from util.fileutil import read_txt
from util.argcheck import parse_iplist
from util.env import get_iplist


def build_userlist(userlist: str) -> List[KinUser]:
    uids = read_txt(userlist, header=False)
    return [KinUser(uid) for uid in uids]


def load_configuration(config_file: str):
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

    userlist_txt = data_dict["userlist"]
    users = build_userlist(userlist_txt)

    return users, shared_argv, private_args
