import os
import json

from navercafe.structs import Cafe, Board


def read_cache(task: Cafe | Board):
    if not isinstance(task, Cafe) and not isinstance(task, Board):
        raise TypeError(f"Invalid type: {type(task)}")
    cache_path = task.cache
    if not os.path.isfile(cache_path):
        return {}
    with open(cache_path, "r", encoding="utf-8") as f:
        json_str = f.read()
    return json.loads(json_str)


def write_cache(task: Cafe | Board, payload):
    if not isinstance(task, Cafe) and not isinstance(task, Board):
        raise TypeError(f"Invalid type: {type(task)}")
    cache_path = task.cache
    json_str = json.dumps(payload, ensure_ascii=False, indent=2)
    with open(cache_path, "w", encoding="utf-8") as f:
        f.write(json_str)
