import yaml
from datetime import datetime
from dateutil.relativedelta import relativedelta
from typing import List

from daumcafelist.structs import QueryPeriod

from util.argcheck import parse_iplist


def build_qplist(query: str, start: str, end: str) -> List[QueryPeriod]:
    # input pattern: yyyymmdd
    start_date = datetime.strptime(start, "%Y%m%d")
    end_date = datetime.strptime(end, "%Y%m%d")

    qp_start = start_date
    qps = []
    while qp_start < end_date:
        qp_end = qp_start + relativedelta(months=1)
        if qp_end > end_date:
            qp_end = end_date
            qp_end = qp_end + relativedelta(days=1)
        # query period format: YYYYMMDD
        qp_start_str = qp_start.strftime("%Y%m%d")
        qp_end_str = qp_end.strftime("%Y%m%d")
        qp = QueryPeriod(query, qp_start_str, qp_end_str)
        qps.append(qp)
        qp_start = datetime.strptime(qp_end_str, "%Y%m%d") + relativedelta(days=1)
    return qps


def load_configuration(config_file: str):
    with open(config_file, "r") as file:
        data_dict = yaml.safe_load(file)

    ips = data_dict["ips"]
    assert len(ips) == 1, "Only one IP is allowed for daumcafe list collector."
    default_interval = data_dict.get("default_interval", 1)
    ips, intervals = parse_iplist(ips, default_interval=default_interval)

    private_args = []
    for ip, interval in zip(ips, intervals):
        argv = {"ip": ip, "interval": interval}
        private_args.append(argv)
    shared_argv = {}

    query = data_dict["query"]
    start = data_dict["start"]
    end = data_dict["end"]
    qplist = build_qplist(query, start, end)
    return qplist, shared_argv, private_args
