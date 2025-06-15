import os
import os.path as osp
import json


from daumcafelist.structs import QueryPeriod, Search


def is_handled_qp(qp: QueryPeriod) -> bool:
    meta_path = qp.meta_savepath
    if not osp.isfile(meta_path):
        return False
    parsed = json.load(open(meta_path, "r", encoding="utf-8"))
    handled = parsed.get("handled", False)
    return handled


def is_handled_search(search: Search) -> bool:
    result_path = search.result_path
    if not osp.isfile(result_path):
        return False
    return True


def is_handled(task: QueryPeriod | Search) -> bool:
    if isinstance(task, QueryPeriod):
        return is_handled_qp(task)
    if isinstance(task, Search):
        return is_handled_search(task)
    raise TypeError(f"Unknown type {type(task)}")
