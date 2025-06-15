import os
import logging
import urllib.parse
import random
import string
from bs4 import BeautifulSoup
from datetime import datetime
from daumnews.handler import get_soup, fetch_html, fetch_json
from daumnews.daumnewsparser import parse_daumnews_soup
from util.env import get_iplist

ips = get_iplist()


def read_cachefile(cache_path):
    with open(cache_path, "r") as f:
        lines = f.readlines()
    return [line.strip() for line in lines]


def write_cachefile(cache_path, data):
    dirr = os.path.dirname(cache_path)
    if not os.path.exists(dirr):
        os.makedirs(dirr)
    with open(cache_path, "w") as f:
        f.write("\n".join(data))


def build_office_cachefile(office_path):
    print("Building office cache file...")
    logger = logging.getLogger(__name__)
    soup = get_soup("https://news.daum.net/cplist", logger=logger, ip=ips[0])
    selector = "#dcc1cfb8-ad2a-4d8b-ba39-32bbd69cde8b > div > dl > dd > div > a"
    tags = soup.select(selector)

    with open(office_path, "w") as f:
        f.write("office\toid\n")
        for tag in tags:
            url = tag["href"]
            if "search?nil" in url:
                continue
            oid = url.split("/")[-2]
            office_name = tag.text.strip()
            f.write(f"{office_name}\t{oid}\n")


def handle_daumnews_html(html, logger, office_name):
    soup = BeautifulSoup(html, "lxml")
    parsed = parse_daumnews_soup(soup, logger, office_name)
    if parsed is None:
        logger.error("Failed to parse %s", office_name)
        return None
    return parsed


def build_office_dictionary(office_path=os.path.join("daumnews", "offices.tsv")):
    if not os.path.isfile(office_path):
        build_office_cachefile(office_path)
    with open(office_path, "r") as f:
        lines = f.readlines()
    office_dict = {}
    for line in lines:
        if line.startswith("office"):
            continue
        office, oid = line.strip().split("\t")
        office_dict[office] = oid
    return office_dict


def build_oid_dict():
    office_dict = build_office_dictionary()
    oid_dict = {}
    for office in office_dict:
        oid = office_dict[office]
        oid_dict[oid] = office
    return oid_dict


OFFICE_DICT = build_office_dictionary()
OID_DICT = build_oid_dict()


def validate_office(name):
    return name in OFFICE_DICT


def validate_oid(oid):
    return oid in OFFICE_DICT.values()


def get_oid(oname):
    return OFFICE_DICT[oname]


def get_office(oid):
    return OID_DICT[oid]


def get_request_body(oid, search_id="", size=30):
    return {
        "variables": {
            "media_home_tab_news_all_7Key": "media_home_news_all",
            "media_home_tab_news_all_7Params": {
                "cpId": oid,
                "size": size,
                "sort": "createDt:desc",
                "searchId": search_id
            }
        },
        "query": """query ($media_home_tab_news_all_7Key: String!, $media_home_tab_news_all_7Params: Object) {
            media_home_tab_news_all_7: page(charonKey: $media_home_tab_news_all_7Key, charonParams: $media_home_tab_news_all_7Params) {
                size
                hasNext
                searchId
                items {
                    title
                    thumbnail
                    mobileLink
                    pcLink
                    meta
                    __typename
                }
                __typename
            }
        }"""
    }


def get_search_id(timestamp):
    s = ''.join(random.choices(string.ascii_uppercase + string.digits, k=8))
    search_id = f"{timestamp}^*|,#-@{s}"
    return search_id.encode().hex()


def parse_uri(uri):
    try:
        parsed = urllib.parse.urlparse(uri)
        idx = parsed.path.split("/")[2]
        return idx
    except:
        return None


def html_save_path(idx):
    return f"data/daumnews/htmls/{idx}.html"


def read_cached_html(idx):
    path = html_save_path(idx)
    if os.path.isfile(path):
        with open(path, "r") as f:
            return f.read()
    return None


def make_jsonl_savedir():
    path = f"data/daumnews/jsonl"
    if not os.path.isdir(path):
        os.makedirs(path)


def jsonl_save_path():
    return f"data/daumnews/jsonl/"


def save_html(idx, html):
    path = html_save_path(idx)

    dirr = os.path.dirname(path)
    if not os.path.exists(dirr):
        os.makedirs(dirr)

    with open(path, "w") as f:
        f.write(html)


def read_cached_or_fetch_html(uri, logger, ip, cache=True):
    aid = parse_uri(uri)
    html = read_cached_html(aid)
    if html:
        logger.info(f"Read cached html: {uri}")
        return html
    html = fetch_html(uri, logger, ip)
    if html is None:
        return None
    if cache:
        save_html(aid, html)
    return html


def day_processed(day, oid):
    cache_path = f"cache/daumnews/{oid}/{day}_articles.txt"

    if not os.path.isfile(cache_path):
        return False

    with open(cache_path, "r") as f:
        cache_lines = f.readlines()

    # remove empty lines
    cache_lines = [line.strip() for line in cache_lines if line.strip()]
    return len(cache_lines) == 0


def process_day(day, oid, ip, logger, save_queue):
    if day_processed(day, oid):
        logger.info("%s, Oid %s, Day %s is already processed",
                    get_office(oid), oid, day)
        return
    day_articles = build_daylist(day, oid, ip, logger)
    if len(day_articles) < 1:
        logger.info("%s, Oid %s, Day %s is empty", get_office(oid), oid, day)
        return

    for i, article in enumerate(day_articles):
        html = read_cached_or_fetch_html(article, logger, ip)
        if html is None:
            continue
        soup = BeautifulSoup(html, "lxml")
        parsed = parse_daumnews_soup(soup, logger, get_office(oid))
        if parsed is None:
            logger.error("Failed to parse %s", article)
            continue
        save_queue.put(parsed)
