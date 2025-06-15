from model.crawler import Crawler
import yaml
import os
from datetime import datetime
from logging import Logger
from typing import Dict, Any, Tuple
from util.argcheck import parse_iplist
from daumnews.daumnews_util import build_office_dictionary, make_jsonl_savedir, day_processed, get_search_id, get_request_body, fetch_json, read_cached_or_fetch_html, write_cachefile, handle_daumnews_html
from util.utils import make_datelist
from util.env import get_iplist


class daumnewsCrawler(Crawler):
    def __init__(self, **kwargs):
        super(daumnewsCrawler, self).__init__()
        self.save_id = "daumnews"
        self.save_dir = "data/daumnews/jsonl"
        self.OFFICEDICT = build_office_dictionary()
        self.OIDDICT = {}
        for office in self.OFFICEDICT:
            oid = self.OFFICEDICT[office]
            self.OIDDICT[oid] = office

    def load_configuration(self, config_file: str):
        with open(config_file, "r") as file:
            data_dict = yaml.safe_load(file)
        if data_dict["excludes"] is None:
            data_dict["excludes"] = []
        office_dict = build_office_dictionary()
        if data_dict["offices"] == "*":
            offices = list(office_dict.keys())
            offices = list(set(offices) - set(data_dict["excludes"]))
        else:
            offices = data_dict["offices"]
            offices = list(set(offices) - set(data_dict["excludes"]))

        start = data_dict["start"]
        end = data_dict["end"]
        ips = data_dict["ips"]
        default_interval = data_dict.get("default_interval", 1)
        if ips is not None:
            ips, intervals = parse_iplist(
                ips, default_interval=default_interval)

        if ips is None or len(ips) == 0:
            ips = get_iplist()
            intervals = [default_interval] * len(ips)

        tasks = []
        daylist = make_datelist(start, end)
        make_jsonl_savedir()
        for day in daylist:
            for office in offices:
                tasks.append((day, office_dict[office]))

        private_args = []
        for ip, interval in zip(ips, intervals):
            argv = {"ip": ip, "interval": interval}
            private_args.append(argv)
        shared_argv = {}
        return tasks, shared_argv, private_args

    def worker_routine(self, payload: Tuple[str, str], shared_argv: Dict[str, Any], private_argv: Dict[str, Any], logger: Logger, save_queue=None):
        day, oid = payload
        logger.warning("Handling office %s", oid)
        ip = private_argv["ip"]
        logger.info("Start processing %s %s", self.get_office(oid), day)
        self.process_day(day, oid, ip, logger, save_queue)
        logger.info("Finished processing %s %s", self.get_office(oid), day)

    def build_daylist(self, day, oid, ip, logger, save_cache=True):
        def get_page_articlelist(day, oid, ip=None):
            # timestamp in milliseconds
            timestamp = datetime.strptime(day, "%Y%m%d").timestamp() * 1000
            articles = []
            uri = f"https://hades-cerberus.v.kakao.com/graphql"
            # timestamp of tomorrow of the day
            timestamp2 = datetime.strptime(
                day, "%Y%m%d").timestamp() + 24 * 60 * 60
            timestamp2 = timestamp2 * 1000
            search_id = get_search_id(timestamp2)
            while True:
                body = get_request_body(oid, search_id)
                response_json = fetch_json(uri, body, logger=logger, ip=ip)
                response_data = response_json['data']['media_home_tab_news_all_7']
                article_list = response_data['items']
                filtered_articles = [article['pcLink']
                                     for article in article_list if article['meta']['createDt'] > timestamp]

                if len(filtered_articles) == 0:
                    break
                articles.extend(filtered_articles)

                if response_data['hasNext']:
                    search_id = response_data['searchId']
                else:
                    logger.warning(f"OID: {oid}, DATE: {day}, No more pages")
                    break

            logger.info(
                f"OID: {oid} DATE: {day}, Found {len(articles)} articles")
            if len(articles) == 0:
                logger.warning(f"OID: {oid}, DATE: {day} empty")
            return articles

        cache_path = os.path.join(
            "cache", "daumnews", oid, f"{day}_articles.txt")
        article_list = []
        article_list = get_page_articlelist(day, oid, ip)
        if save_cache:
            write_cachefile(cache_path, article_list)
        return article_list

    def process_day(self, day, oid, ip, logger, save_queue):
        if day_processed(day, oid):
            logger.info("%s, Oid %s, Day %s is already processed",
                        self.get_office(oid), oid, day)
            return
        day_articles = self.build_daylist(day, oid, ip, logger)
        if len(day_articles) < 1:
            logger.info("%s, Oid %s, Day %s is empty",
                        self.get_office(oid), oid, day)
            return

        for article in day_articles:
            html = read_cached_or_fetch_html(article, logger, ip)
            if html is None:
                continue
            parsed = handle_daumnews_html(html, logger, self.get_office(oid))
            if parsed is None:
                continue
            save_queue.put(parsed)

    def validate_office(self, name):
        return name in self.OFFICEDICT

    def validate_oid(self, oid):
        return oid in self.OFFICEDICT.values()

    def get_oid(self, office):
        return self.OFFICEDICT[office]

    def get_office(self, oid):
        return self.OIDDICT[oid]
