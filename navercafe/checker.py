import os
from typing import Any, Dict, List
import datetime
from dateutil.relativedelta import relativedelta

from navercafe.structs import Cafe, Board
from util.fileutil import count_file_lines
from navercafe.cache import read_cache


def mark_done(entry: Dict[str, Any]):
    entry["done"] = True
    entry["timestamp"] = datetime.datetime.now().isoformat()
    return entry


def duration_passed(entry: Dict[str, Any]) -> bool:
    timestamp = entry.get("timestamp", None)
    if timestamp is None:
        return True
    # if one month has passed, reprocess
    timestamp = datetime.datetime.fromisoformat(timestamp)
    if timestamp + relativedelta(months=1) < datetime.datetime.now():
        return True

    return False


def check_done(entry: Dict[str, Any]):
    done = entry.get("done", False)
    if not done:
        return False
    if duration_passed(entry):
        return False
    return True


def is_processed(task: Cafe | Board) -> bool:
    if not isinstance(task, Cafe) and not isinstance(task, Board):
        raise TypeError(f"Invalid type: {type(task)}")
    parsed = read_cache(task)
    if parsed is None:
        return False
    return check_done(parsed)
