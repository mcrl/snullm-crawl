from typing import List, Optional
import json

from daumcafelist.structs import QueryPeriod, Search


def read_cache_qp(qp: QueryPeriod) -> List[str]:
    parsed = json.load(open(qp.meta_savepath, "r", encoding="utf-8"))
    return parsed["result"]


def read_cache_search(search: Search) -> List[str]:
    parsed = json.load(open(search.result_path, "r", encoding="utf-8"))
    return parsed["result"]


def write_cache_qp(qp: QueryPeriod, result: List[str]):
    payload = {}
    payload["done"] = True
    payload["result"] = result
    cache_path = qp.meta_savepath
    # write the json dump
    with open(cache_path, "w", encoding="utf-8") as f:
        f.write(json.dumps(payload, ensure_ascii=False, indent=2))


def write_cache_search(search: Search, result: List[str], count):
    payload = {}
    payload["count"] = count
    payload["done"] = True
    payload["result"] = result
    with open(search.result_path, "w", encoding="utf-8") as f:
        f.write(json.dumps(payload, ensure_ascii=False, indent=2))


def read_cache(task: QueryPeriod | Search) -> str:
    if isinstance(task, QueryPeriod):
        return read_cache_qp(task)
    if isinstance(task, Search):
        return read_cache_search(task)
    raise TypeError(f"Unknown type {type(task)}")


def write_cache(
    task: QueryPeriod | Search, result: List[str], count: Optional[int] = None
):
    if isinstance(task, QueryPeriod):
        return write_cache_qp(task, result)
    if isinstance(task, Search):
        return write_cache_search(task, result, count)
    raise TypeError(f"Unknown type {type(task)}")
