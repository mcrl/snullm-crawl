from navernews.navernews_util import (
    read_cached_or_fetch_html,
    build_daylist,
)
from navernews.navernewsparser import handle_navernews_html
import os
import traceback


def process_day(ip, logger, save_queue, day, oid, office):
    # get days
    # this function leaves cache at cache/navernews/{oid}/{day}.txt
    day_articles = build_daylist(day, oid, ip, logger, check_yesterday=True)

    # remove done files
    # this function gets cache at cache/navernews/{oid/done/{day}.txt
    done_path = f"cache/navernews/{oid}/done/{day}.txt"
    done = []
    if os.path.isfile(done_path):
        with open(done_path, "r") as f:
            done = f.readlines()
    # done = [line.strip() for line in done if line.strip()]
    # for this time, we disable the done step
    done = []

    # this allows us to check if the day has been processed
    # if processed, we can skip the day
    to_process = [article for article in day_articles if article not in done]
    if len(to_process) == 0:
        logger.info("Offcie %s Day %s is already processed", office, day)
        return
    logger.info("Processing %s articles", len(to_process))

    # for every undone articles
    # get article
    with open(done_path, "a") as f:
        for article in to_process:
            res = read_cached_or_fetch_html(article, logger, ip)
            if res is None:
                continue
            html, real_uri = res
            f.write(article)
            f.write("\n")
            if html is None:
                continue
            try:
                parsed = handle_navernews_html(
                    html, logger, office, uri=article, real_uri=real_uri
                )
            except Exception as e:
                print(traceback.format_exc())
                parsed = None
            if parsed is None:
                logger.error(f"process_day:Failed to parse {article}")
                continue
            save_queue.put(parsed)

    # put to save_queue

    # leave cache on cache/navernews/{oid}/done/{day}.txt
