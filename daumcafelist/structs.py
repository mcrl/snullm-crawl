import os
import os.path as osp
from urllib.parse import urlencode

DATA_BASE = "data/daumcafe_id"


class QueryPeriod:
    query = None  # type: str
    start = None  # type: str
    end = None  # type: str
    save_dir = None  # type: str
    meta_savepath = None  # type: str

    def __init__(self, query: str, start: str, end: str):
        """start, end date format should be YYYYMMDD"""
        self.query = query
        self.start = start
        self.end = end
        interquery = query.replace("/", "_")
        start, end = start.replace("/", ""), end.replace("/", "")
        dirname = f"{interquery}/{start}_{end}"
        self.save_dir = osp.join(DATA_BASE, dirname)
        self.meta_savepath = osp.join(self.save_dir, "meta.json")
        if not osp.isdir(self.save_dir):
            os.makedirs(self.save_dir, exist_ok=True)

    def __str__(self):
        return f"{self.query} | from: {self.start} | to: {self.end}"


class Search:
    qp = None  # type: QueryPeriod
    num = 100  # type:int
    result_id = None  # type:int
    uri = None  # type:str
    html_path = None  # type:str
    result_path = None  # type:str

    def __init__(self, qp: QueryPeriod, result_id: int, num: int = 100):
        self.qp = qp
        self.num = num
        self.result_id = result_id

        start = qp.start
        end = qp.end
        query = qp.query

        self.query = query
        self.start = start
        self.end = end
        self.result_path = osp.join(qp.save_dir, f"{result_id}.json")

    def __str__(self):
        return f"{self.qp} | idx: {self.result_id}"
