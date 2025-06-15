import os
from typing import List
import json
import gzip
import functools

CACHE_BASE = "cache/navercafe"
DATA_BASE = "data/navercafe"

CAFE_ARTICLE_CHECK = DATA_BASE
BATCH_SIZE = 100000


@functools.lru_cache(maxsize=256)
def get_article_cache_content(cafe, board, batchid):
    cafe_dir = os.path.join(CAFE_ARTICLE_CHECK, cafe)
    board_dir = os.path.join(cafe_dir, board)
    cache_dir = os.path.join(board_dir, "cache")
    cache_path = os.path.join(cache_dir, f"{board}_{batchid}.txt")
    if not os.path.exists(cache_path):
        return set()
    with open(cache_path, "r") as f:
        lines = f.readlines()
    return set([int(line.split(".")[0].strip()) for line in lines])


class Cafe:
    cafeid: str
    cafe_internalid: str
    cache_dir: str
    boardlist_cache = None  # type: str

    def __init__(self, cafeid):
        self.cafeid = cafeid
        self.cache_dir = os.path.join(CACHE_BASE, cafeid)
        self.cache = os.path.join(self.cache_dir, "cafecache.json")

        # make cache dir if not exists
        if not os.path.isdir(self.cache_dir):
            os.makedirs(self.cache_dir)

    def __str__(self):
        return f"Cafe({self.cafeid})"


class Board:
    cafe: Cafe
    path: str
    bid: str
    bname: str
    cache_dir: str
    cache = None  # type: str
    board_jsonl_savepath = None  # type: str

    def __init__(self, cafe: Cafe, bid: str, bname: str):
        self.cafe = cafe
        self.bid = bid
        self.bname = bname
        self.path = f"/{cafe.cafeid}/{bid}"

        self.cache_dir = os.path.join(cafe.cache_dir, bid)
        self.cache = os.path.join(self.cache_dir, "boardcache.json")
        data_dir = os.path.join(DATA_BASE, cafe.cafeid, bid)
        self.board_jsonl_savepath = os.path.join(data_dir, "board.jsonl")

        # make board cache dir and data dir if not exists
        if not os.path.isdir(self.cache_dir):
            os.makedirs(self.cache_dir, exist_ok=True)
        if not os.path.isdir(data_dir):
            os.makedirs(data_dir, exist_ok=True)
        if not os.path.isdir(os.path.join(data_dir, "json_files")):
            os.makedirs(os.path.join(data_dir, "json_files"), exist_ok=True)

    def __str__(self):
        return f"{self.cafe.cafeid} {self.bname}({self.bid})"


class Article:
    board: Board
    path: str
    aid: str
    title = None  # type: str
    retrieved = None  # type: str
    posted = None  # type: str
    text = None  # type: str
    json_path = None  # type: str
    uri = None

    def __init__(self, board: Board, aid: str):
        self.board = board
        self.aid = aid
        self.path = f"{board.path}/{aid}"

        html_dir = os.path.join(
            DATA_BASE, board.cafe.cafeid, board.bid, "json_files")
        self.json_path = os.path.join(html_dir, aid + ".json")
        self.gz_path = self.json_path + ".gz"
        self.uri = f"https://m.cafe.naver.com/{board.cafe.cafeid}/{aid}"

    def to_json(self, ignore=True):
        if self.text is None:
            if ignore:
                return
            raise Exception("Article text is not set")
        payload = {
            "title": self.title,
            "retrieval_date": self.retrieved,
            "posted": self.posted,
            "text": self.text,
            "uri": self.uri,
            "type": "navercafe",
        }
        return json.dumps(payload, ensure_ascii=False)

    def __str__(self):
        return (
            f"{self.board.cafe.cafeid} {self.board.bname}({self.board.bid}) {self.aid}"
        )

    def __hash__(self) -> int:
        return hash(self.uri)

    def _cache_exist(self) -> bool:
        batchid = int(self.aid) // BATCH_SIZE
        cached_article_set = get_article_cache_content(
            self.board.cafe.cafeid, self.board.bid, batchid
        )
        return int(self.aid) in cached_article_set

    def is_processed(self):
        return (
            os.path.exists(self.json_path)
            or os.path.exists(self.gz_path)
            or self._cache_exist()
        )

    def write_json(self, data):
        dumped = json.dumps(data, ensure_ascii=False, indent=2)
        with gzip.open(self.gz_path, "wt") as f:
            f.write(dumped)

    def read_json(self):
        if os.path.exists(self.json_path):
            with open(self.json_path, "r") as f:
                return json.load(f)
        elif os.path.exists(self.gz_path):
            with gzip.open(self.gz_path, "rt") as f:
                return json.load(f)
        return None
