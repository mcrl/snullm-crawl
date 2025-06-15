from logging import Logger
from typing import List, Tuple, Dict, Any
from bs4 import BeautifulSoup
import os.path as osp
import json
import time

import requests
import traceback

from daumcafelist.structs import Search, QueryPeriod
from daumcafelist.checker import is_handled
import daumcafelist.cache as gcache


from util.misc import get_interval




def handle_search(
    search: Search, ip: str, google_api_key: str, google_search_engine: str, logger: Logger, interval: int = 1
) -> Tuple[int, List[str]]:
    # only extract IDs
    # https://m.cafe.daum.net/S2000
    def _extract_id(url: str) -> str:
        parts = url.split("/")
        # find this
        find_path = "m.cafe.daum.net"
        idx = parts.index(find_path) + 1
        return parts[idx] if idx < len(parts) else ""
    msg = f"Start Handling Search {search}"
    json_path = search.result_path
    logger.info("Checking result path %s", json_path)
    response = {}
    if osp.isfile(json_path):
        try:
            response = json.load(open(json_path, "r", encoding="utf-8"))
        except json.JSONDecodeError as e:
            logger.error(f"Failed to load JSON from {json_path}: {e}")
            response = {}
        
    if not response:
        url = 'https://www.googleapis.com/customsearch/v1'

        params = {
            "key": google_api_key,
            "cx": google_search_engine,
            "q": search.query,
            "after": search.start,
            "before": search.end,
            "num": 10,
            "start": search.result_id,
            # "sort": f"date:r:{search.start}:{search.end}",
        }
        # print(params["sort"])
        response = requests.get(url, params=params).json()
        # get response 
        with open(search.result_path, "w", encoding="utf-8") as f:
            f.write(json.dumps(response, ensure_ascii=False, indent=2))
    items = response.get("items", [])
    if not items:
        msg = f"No items found for search {search}"
        logger.info(msg)
        return [], None
    urls = [item["formattedUrl"] for item in items]
    urls = [url for url in urls if url.startswith("https://m.cafe.daum.net/")]
    ids = [{"id": _extract_id(url).strip()} for url in urls]
    ids = [id_ for id_ in ids if id_["id"]]
    
    next_start = response.get("queries", {}).get("nextPage", [{}])[0].get("startIndex", None)
    return ids, next_start

   


def handle_query_period(
    qp: QueryPeriod,
    shared_argv: Dict[str, Any],
    prive_argv: Dict[str, Any],
    logger: Logger,
    save_queue=None
) -> List[str]:
    if is_handled(qp):
        msg = f"Query period {qp} is already handled"
        logger.info(msg)
        return

    ip = prive_argv["ip"]
    interval = get_interval(shared_argv, prive_argv)

    idx = 0
    results = []
    msg = f"Start Handling QueryPeriod {qp}"
    num = 10
    google_api_key = shared_argv["google_api_key"]
    google_search_engine = shared_argv["google_search_engine"]
    NEXT_MAX = 100
    next_max = NEXT_MAX
    
    while idx < next_max:
        try:
            msg = f"Query period {qp} is being handled with idx {idx}"
            logger.info(msg)
            search = Search(qp, idx, num=num)
            result, next = handle_search(search, ip, google_api_key, google_search_engine, logger, interval)
            results.extend(result)
            if next is None or next <= idx:
                msg = f"Query period {qp} is done with idx {idx}"
                logger.info(msg)
                break
            next_max = min(next, NEXT_MAX)
            idx += 1
            time.sleep(interval)

        except Exception as e:
            msg = f"Search {search} failed with exception {e}"
            logger.error(msg)
            idx += 1
            time.sleep(interval)


    id_set = set(results)
    id_list = list(id_set)
    gcache.write_cache(qp, id_list)
    for id_ in id_list:
        save_queue.put(json.dumps(id_, ensure_ascii=False))
    # return id_list
