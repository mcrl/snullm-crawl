from typing import List
from model.crawler import Crawler
import yaml
import os

from daumcafelist.handler import handle_query_period
from util.argcheck import parse_iplist
from util.argcheck import parse_iplist
from datetime import datetime
from dateutil.relativedelta import relativedelta
from daumcafelist.structs import QueryPeriod



def build_qplist(query: str, start: str, end: str) -> List[QueryPeriod]:
    # input pattern: yyyymmdd
    start_date = datetime.strptime(start, "%Y%m%d")
    end_date = datetime.strptime(end, "%Y%m%d")

    qp_start = start_date
    qps = []
    while qp_start < end_date:
        qp_end = qp_start + relativedelta(months=1) - relativedelta(days=1)
        if qp_end > end_date:
            qp_end = end_date
        # query period format: YYYYMMDD
        qp_start_str = qp_start.strftime("%Y%m%d")
        qp_end_str = qp_end.strftime("%Y%m%d")
        qp = QueryPeriod(query, qp_start_str, qp_end_str)
        qps.append(qp)
        qp_start = datetime.strptime(
            qp_end_str, "%Y%m%d") + relativedelta(days=1)
    return qps


class daumcafeIDCrawler(Crawler):
    def __init__(self, **kwargs):
        super(daumcafeIDCrawler, self).__init__()
        self.save_id = "daumcafe_id"
        self.save_dir = "data/daumcafe_id"

    def load_configuration(self, config_file: str):
        with open(config_file, "r") as file:
            data_dict = yaml.safe_load(file)

        ips = data_dict["ips"]
        default_interval = data_dict.get("default_interval", 1)
        ips, intervals = parse_iplist(ips, default_interval=default_interval)
        
        

        private_args = []
        for ip, interval in zip(ips, intervals):
            argv = {"ip": ip, "interval": interval}
            private_args.append(argv)

        google_api_key = data_dict["google_api_key"]
        google_search_engine = data_dict["google_search_engine"]
        shared_argv = {
            "google_api_key": google_api_key,
            "google_search_engine": google_search_engine
        }

        query = data_dict["query"]
        start = data_dict["start"]
        end = data_dict["end"]
        
        
        qplist = build_qplist(query, start, end)
        return qplist, shared_argv, private_args



    def worker_routine(self, *args, **kwargs):
        handle_query_period(*args, **kwargs)
        
