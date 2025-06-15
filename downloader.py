import os
import socket
import time
import traceback
from argparse import ArgumentParser
from engine.engine import Engine
from util.slack import send_slack_message
from daumcafe.daumcafe_crawler import daumcafeCrawler
from daumnews.daumnews_crawler import daumnewsCrawler
from navercafe.navercafe_crawler import navercafeCrawler
from navernews.navernews_crawler import navernewsCrawler
from naverblog.naverblog_crawler import naverblogCrawler
from cafelist.navercafe_id_crawler import navercafeIDCrawler
from daumcafelist.crawler import daumcafeIDCrawler  

crawling_tasks = {"daumcafe": daumcafeCrawler, "navercafe": navercafeCrawler,
                  "daumnews": daumnewsCrawler, "navernews": navernewsCrawler,
                  "naverblog": naverblogCrawler}
onetime_tasks = {"navercafe_id": navercafeIDCrawler, 
                 "daumcafe_id": daumcafeIDCrawler}

def init():
    parser = ArgumentParser()
    parser.add_argument("--config", required=True,
                        help="Task Configuration File")
    parser.add_argument("--task", required=True, help="Task Name")
    args = parser.parse_args()
    return args


def main(args):
    config_path = args.config
    crawling_task = args.task
    if crawling_task not in crawling_tasks.keys() and crawling_task not in onetime_tasks.keys():
        print(f"Task {crawling_task} is not supported")
        return
    # Convert config_path to absolute path from project root
    # if not os.path.isabs(config_path):
    #     project_root = os.path.dirname(os.path.abspath(__file__))
    #     config_path = os.path.join(project_root, config_path)
    print(f"Using configuration file: {config_path}")
    if crawling_task in crawling_tasks.keys():
        crawler = crawling_tasks[crawling_task]()
    else:
        crawler = onetime_tasks[crawling_task]()
    tasks, shared_argv, private_args = crawler.load_configuration(config_path)
    save_id = crawler.save_id
    save_dir = crawler.save_dir

    if not os.path.exists(save_dir):
        os.makedirs(save_dir)
    engine = Engine(use_saver=True, task_name=crawling_task)
    engine.launch_workers(crawler.worker_routine, shared_argv, private_args)
    engine.enqueue_tasks(tasks)
    engine.enqueue_stopwork()
    engine.launch_saver(save_id, save_dir)

    while True:
        time.sleep(5)
        if engine.poll_routine():
            break


if __name__ == "__main__":
    # get hostname
    hostname = socket.gethostname()
    args = init()
    heading = f"[{hostname}:{args.task}]"

    try:
        msg = f"{heading}\nStarting Task"
        send_slack_message(msg)
        main(args)
        msg = f"{heading}\nTask successfully ended"
        send_slack_message(msg)
    except Exception as e:
        msg = f"{heading}\nException occurred: {e}"
        msg += "\n\n" + traceback.format_exc()
        print(msg)
        send_slack_message(msg)
