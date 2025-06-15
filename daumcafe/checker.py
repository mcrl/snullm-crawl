import os

from daumcafe.structs import Cafe, Board
from util.fileutil import count_file_lines
from daumcafe.cache import read_cafe_cachefile, read_board_cachefile
import time


def board_is_processed(board: Board):
    if not os.path.isdir(board.cache_dir):
        return False
    if not os.path.isfile(board.board_jsonl_savepath):
        return False
    if not os.path.isfile(board.articlelist_cache):
        return False

    # check if board cache file is up-to-date. We regard it is stale if 1 month has passed since the last update.
    if (time.time() - os.path.getmtime(board.articlelist_cache)) > 30 * 24 * 60 * 60:
        return False

    articles = read_board_cachefile(board)
    article_count = len(articles)
    line_count = count_file_lines(board.board_jsonl_savepath)
    if article_count != line_count:
        return False
    return True


def cafe_is_processed(cafe: Cafe):
    # if cache dir does not exist, return False
    if not os.path.isdir(cafe.cache_dir):
        return False

    # if cache file does not exist, return False
    if not os.path.isfile(cafe.boardlist_cache):
        return False

    boards = read_cafe_cachefile(cafe)
    if len(boards) == 0:
        return False

    for board in boards:
        if not board_is_processed(board):
            return False

    return True


def is_processed(task: Cafe | Board) -> bool:
    if isinstance(task, Cafe):
        return cafe_is_processed(task)
    if isinstance(task, Board):
        return board_is_processed(task)
    raise TypeError(f"task must be Cafe or Board, not {type(task)}")
