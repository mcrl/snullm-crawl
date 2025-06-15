import os
from typing import List
import json
import gzip
import functools

CACHE_BASE = "cache/daumcafe"
DATA_BASE = "data/daumcafe"


class Cafe:
    cafeid: str
    cache_dir: str
    boardlist_cache = None  # type: str

    def __init__(self, cafeid):
        self.cafeid = cafeid
        self.cache_dir = os.path.join(CACHE_BASE, cafeid)
        self.boardlist_cache = os.path.join(self.cache_dir, "boards.tsv")

        # make cache dir if not exists
        if not os.path.isdir(self.cache_dir):
            os.makedirs(self.cache_dir, exist_ok=True)

    def __str__(self):
        return f"Cafe({self.cafeid})"


class Board:
    cafe: Cafe
    path: str
    bid: str
    btype: str
    bname: str
    cache_dir: str
    articlelist_cache = None  # type: str
    board_jsonl_savepath = None  # type: str

    def __init__(self, cafe: Cafe, bid: str, btype: str, bname: str):
        self.cafe = cafe
        self.bid = bid
        self.btype = btype
        self.bname = bname
        self.path = f"/{cafe.cafeid}/{bid}"

        self.cache_dir = os.path.join(cafe.cache_dir, bid)
        self.articlelist_cache = os.path.join(self.cache_dir, "aids.txt")
        data_dir = os.path.join(DATA_BASE, cafe.cafeid, bid)
        self.board_jsonl_savepath = os.path.join(data_dir, "board.jsonl")

        # make board cache dir and data dir if not exists
        if not os.path.isdir(self.cache_dir):
            os.makedirs(self.cache_dir, exist_ok=True)
        if not os.path.isdir(data_dir):
            os.makedirs(data_dir, exist_ok=True)
        if not os.path.isdir(os.path.join(data_dir, "htmls")):
            os.makedirs(os.path.join(data_dir, "htmls"), exist_ok=True)

    def __str__(self):
        return f"{self.cafe.cafeid} {self.bname}({self.bid})"


@functools.lru_cache(maxsize=128)
def get_done_cache(cafeid, bid, batch_no):
    cache_dir = os.path.join(DATA_BASE, cafeid)
    cache_path = os.path.join(cache_dir, f"{bid}_{batch_no}.txt")
    if os.path.exists(cache_path):
        with open(cache_path, "r") as f:
            lines = f.readlines()
        return set([l.strip() for l in lines])
    return set()


class Article:
    board: Board
    path: str
    aid: str
    title = None  # type: str
    retrieved = None  # type: str
    posted = None  # type: str
    text = None  # type: str
    html_data_path = None  # type: str
    uri = None

    def __init__(self, board: Board, aid: str):
        self.board = board
        self.aid = aid
        self.path = f"{board.path}/{aid}"

        self.html_data_path = os.path.join(
            DATA_BASE, board.cafe.cafeid, board.bid, "htmls", aid + ".html"
        )
        self.gz_path = self.html_data_path + ".gz"
        self.uri = f"https://m.cafe.daum.net/{board.cafe.cafeid}/{board.bid}/{aid}"

    def to_json(self, ignore=True):
        if self.text is None:
            if ignore:
                return
            raise Exception("Article text is not set")
        payload = {
            "title": self.title,
            "retrieved": self.retrieved,
            "posted": self.posted,
            "text": self.text,
            "uri": self.uri,
        }
        return json.dumps(payload, ensure_ascii=False)

    def __str__(self):
        return (
            f"{self.board.cafe.cafeid} {self.board.bname}({self.board.bid}) {self.aid}"
        )

    def __hash__(self) -> int:
        return hash(self.uri)

    def is_downloaded(self):
        if os.path.exists(self.html_data_path):
            # self.convert_html_to_gzip() TODO: we need to convert all html to gzip, but not now, as of 24-11.
            return True
        elif os.path.exists(self.gz_path):
            return True
        batch_id = int(self.aid) // 10000
        done_cache = get_done_cache(
            self.board.cafe.cafeid, self.board.bid, batch_id)
        if f"{self.aid}.html" in done_cache:
            return True
        return False

    def load_from_file(self):
        if os.path.exists(self.html_data_path):
            with open(self.html_data_path, "r") as f:
                return f.read()
        elif os.path.exists(self.gz_path):
            with gzip.open(self.gz_path, "rt") as f:
                return f.read()
        return None

    def save_html(self, html):
        with gzip.open(self.gz_path, "wt") as f:
            f.write(html)

    def _convert_html_to_gzip(self):
        with open(self.html_data_path, "r") as f:
            html = f.read()
            self.save_html(html)
            os.remove(self.html_data_path)

    def convert_html_to_gzip(self):
        if os.path.exists(self.html_data_path):
            self._convert_html_to_gzip()
