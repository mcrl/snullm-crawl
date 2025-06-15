import os
from typing import List, Dict
import json
import datetime
import time


CACHE_BASE = "cache/kin"
DATA_BASE = "data/kin"
KIN_BEST_CACHE_BASE = "cache/kin_best"
KIN_BEST_DATA_BASE = "data/kin_best"


def make_dir(cache_path):
    os.makedirs(os.path.dirname(cache_path), exist_ok=True)


def no_cache(cache_path):
    return not os.path.exists(cache_path) or os.path.getsize(cache_path) <= 0


def save_cache_routine(entry, cache_path):
    entry["timestamp"] = time.time()
    make_dir(cache_path)
    with open(cache_path, "w") as f:
        json.dump(entry, f, indent=2, ensure_ascii=False)


class Document:
    question: str
    answers: List[str]
    dirId: int
    docId: int

    def __init__(self, dirId, docId):
        self.dirId = dirId
        self.docId = docId
        self.answers = []
        self.title = ""
        self.question = ""
        self.retrieved_at = time.time()
        if os.path.exists(self.save_path):
            self.retrieved_at = os.path.getmtime(self.save_path)
        self.question_badges = []
        make_dir(self.save_path)

    def __str__(self):
        return f"Document({self.dirId}, {self.docId})"

    @property
    def save_path(self):
        return os.path.join(DATA_BASE, str(self.dirId), f"{self.docId}.html")

    @property
    def url(self):
        return f"https://kin.naver.com/qna/detail.naver?dirId={self.dirId}&docId={self.docId}"

    def to_json(self):
        # 2024-07-03T15:00:00Z
        retrieval_date = datetime.datetime.fromtimestamp(self.retrieved_at).strftime(
            "%Y-%m-%dT%H:%M:%SZ"
        )
        entry = {
            "url": self.url,
            "title": self.title,
            "question": self.question,
            "question_badges": self.question_badges,
            "answers": self.answers,
            "retrieval_date": retrieval_date,
        }
        return json.dumps(entry, ensure_ascii=False)


class KinBestDir:
    dirId: int
    max_pages: int
    done = False

    def __init__(self, dirId, max_pages):
        self.dirId = dirId
        self.max_pages = max_pages
        self.done = False

    @property
    def cache_path(self):
        return os.path.join(KIN_BEST_CACHE_BASE, str(self.dirId).zfill(6) + ".json")

    def restore_from_cache(self):
        if no_cache(self.cache_path):
            return
        with open(self.cache_path) as f:
            data = json.load(f)
            self.max_pages = data.get("max_pages", 0)
            self.done = data.get("done", False)

    def save_to_cache(self):
        entry = {"max_pages": self.max_pages, "done": self.done}
        save_cache_routine(entry, self.cache_path)


class KinBestPage:
    dirId: int
    pageId: int
    documents: List[Document]
    done = False

    def __init__(self, dirId, pageId):
        self.dirId = dirId
        self.pageId = pageId
        self.documents = []
        self.done = False

    @property
    def cache_path(self):
        return os.path.join(
            KIN_BEST_CACHE_BASE,
            str(self.dirId).zfill(6),
            str(self.pageId).zfill(6) + ".json",
        )

    def restore_from_cache(self):
        if no_cache(self.cache_path):
            return
        with open(self.cache_path) as f:
            data = json.load(f)
            self.documents = [Document(**doc)
                              for doc in data.get("documents", [])]
            self.done = data.get("done", False)

    def save_to_cache(self):
        entry = {
            "documents": [
                {"dirId": doc.dirId, "docId": doc.docId} for doc in self.documents
            ],
            "done": self.done,
        }
        save_cache_routine(entry, self.cache_path)


class KinUser:
    # https://kin.naver.com/userinfo/answerList.naver?u=7OXjQaYCtNMO9Zhg7Bt18DXE3tYYrsB6Q54WZxy0UlI%3D
    userId: str
    username: str
    dirIds: List[Dict[int, bool]]
    years: List[int]
    user_docs: List[Document]
    ready = False
    metainfo_ready = False

    def __init__(self, userId):
        self.userId = userId
        self.username = ""
        self.dirIds = []
        self.years = []
        self.user_docs = []
        self.ready = False
        self.metainfo_ready = False
        self.cache_timestamp = 0
        make_dir(self.cache_path)

    @property
    def cache_path(self):
        return os.path.join(CACHE_BASE, "user", self.userId + ".json")

    def restore_from_cache(self):
        if no_cache(self.cache_path):
            return
        mtime = os.path.getmtime(self.cache_path)
        with open(self.cache_path) as f:
            data = json.load(f)
            self.userId = data.get("userId", self.userId)
            self.username = data.get("username", "")
            self.dirIds = data.get("dirIds", [])
            self.years = data.get("years", [])
            self.user_docs = [
                Document(doc["dirId"], doc["docId"])
                for doc in data.get("user_docs", [])
            ]
            self.ready = data.get("ready", False)
            self.metainfo_ready = data.get("metainfo_ready", False)
            self.cache_timestamp = data.get("timestamp", mtime)

    def save_to_cache(self):
        entry = {
            "userId": self.userId,
            "username": self.username,
            "dirIds": self.dirIds,
            "years": self.years,
            "user_docs": [
                {"dirId": doc.dirId, "docId": doc.docId} for doc in self.user_docs
            ],
            "ready": self.ready,
            "metainfo_ready": self.metainfo_ready,
            "timestamp": time.time(),
        }
        save_cache_routine(entry, self.cache_path)

    @property
    def save_path(self):
        return os.path.join(CACHE_BASE, "user", self.userId + ".html")

    def __str__(self):
        return f"KinUser({self.userId}/{self.username})"
