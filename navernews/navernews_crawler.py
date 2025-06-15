from model.crawler import Crawler
from typing import List
import yaml
import util.utils as util
import navernews.navernews_util as navernews_util
import navernews.worker
from util.argcheck import parse_iplist
from logging import Logger
import traceback
import os
from util.env import get_iplist


class navernewsCrawler(Crawler):
    def __init__(self, **kwargs):
        super(navernewsCrawler, self).__init__()
        self.save_id = "navernews"
        self.save_dir = "data/navernews_merged"
        self.cache_dir = "cache/navernews"
        self.OFFICEDICT = navernews_util.build_office_dictionary()
        self.OIDDICT = {}
        for office in self.OFFICEDICT:
            oid = self.OFFICEDICT[office]
            self.OIDDICT[oid] = office

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
        tasks = []

        offices = data_dict["offices"]
        date_range = util.make_datelist(
            data_dict["start"], data_dict["end"]
        )
        office_dict = navernews_util.build_office_dictionary()
        oids = [office_dict[office] for office in offices]

        for oid in oids:
            navernews_util.make_officedir(oid)

        for day in date_range:
            for oid in oids:
                tasks.append((day, oid))

        return tasks, shared_argv, private_args

    def load_save_configuration(self, config_file: str):
        with open(config_file, "r") as file:
            data_dict = yaml.safe_load(file)
        save_id = data_dict["save_id"]
        save_dir = data_dict["save_dir"]
        return save_id, save_dir

    def worker_routine(self, payload: List[str], shared_argv: dict, private_argv: dict, logger: Logger, save_queue=None):
        day, oid = payload
        office = self.get_office(oid)
        ip = private_argv["ip"]
        interval = private_argv["interval"]
        logger.info("Start processing %s %s", office, day)
        navernews.worker.process_day(
            ip, logger, save_queue, day, oid, interval)
        logger.info("Finished processing %s %s", office, day)

    def process_day(self, ip, logger, save_queue, day, oid, office):
        # get days
        # this function leaves cache at cache/navernews/{oid}/{day}.txt
        day_articles = navernews_util.build_daylist(
            day, oid, ip, logger, check_yesterday=True)
        # remove done files
        # this function gets cache at cache/navernews/{oid/done/{day}.txt
        done_path = os.path.join(self.cache_dir, oid, "done", f"{day}.txt")
        done = []
        if os.path.isfile(done_path):
            with open(done_path, "r") as f:
                done = f.readlines()
        # done = [line.strip() for line in done if line.strip()]
        # for this time, we disable the done step
        done = []

        # this allows us to check if the day has been processed
        # if processed, we can skip the day
        to_process = [
            article for article in day_articles if article not in done]
        if len(to_process) == 0:
            logger.info("Offcie %s Day %s is already processed", office, day)
            return
        logger.info("Processing %s articles", len(to_process))

        # for every undone articles
        # get article
        with open(done_path, "a") as f:
            for article in to_process:
                res = navernews_util.read_cached_or_fetch_html(
                    article, logger, ip)
                if res is None:
                    continue
                html, real_uri = res
                f.write(article)
                f.write("\n")
                if html is None:
                    continue
                try:
                    parsed = navernews_util.handle_navernews_html(
                        html, logger, office, uri=article, real_uri=real_uri
                    )
                except Exception as e:
                    logger.error(f"Error parsing {article}")
                    logger.error(traceback.format_exc())
                    parsed = None
                if parsed is None:
                    logger.error(f"process_day:Failed to parse {article}")
                    continue
                save_queue.put(parsed)

        # put to save_queue
        # leave cache on cache/navernews/{oid}/done/{day}.txt

    def validate_office(self, name):
        return name in self.OFFICEDICT

    def validate_oid(self, oid):
        return oid in self.OFFICEDICT.values()

    def get_oid(self, office):
        return self.OFFICEDICT[office]

    def get_office(self, oid):
        return self.OIDDICT[oid]
