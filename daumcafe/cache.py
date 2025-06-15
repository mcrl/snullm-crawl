import os
from typing import List

from daumcafe.structs import Cafe, Board, Article
from util.fileutil import read_tsv, read_txt
import time


def read_cafe_cachefile(cafe: Cafe) -> List[Board]:
    if not os.path.isfile(cafe.boardlist_cache):
        raise FileNotFoundError
    entries = read_tsv(cafe.boardlist_cache)

    boards = []
    for entry in entries:
        if len(entry) < 3:
            continue
        board = Board(cafe, entry[0], entry[1], entry[2])
        boards.append(board)
    return boards


def read_board_cachefile(board: Board) -> List[Article]:
    if not os.path.isfile(board.articlelist_cache):
        return None
    # if file has been updated more than 30 days ago, we regard it as stale.
    if (time.time() - os.path.getmtime(board.articlelist_cache)) > 30 * 24 * 60 * 60:
        return None
    entries = read_txt(board.articlelist_cache)
    if len(entries) == 0:
        return []
    if entries[0] == "<<Unauthorized>>":
        return []
    articles = map(lambda entry: Article(board, entry), entries)
    return list(articles)


def write_cafe_cachefile(cafe: Cafe, boardlist: List[Board]):
    with open(cafe.boardlist_cache, "w", encoding="utf-8") as f:
        f.write("bid\tbytpe\tbname\n")
        for board in boardlist:
            f.write(f"{board.bid}\t{board.btype}\t{board.bname}\n")


def write_articlelist_cachefile(
    board: Board, articlelist: List[Article], unauthorized=False
):
    with open(board.articlelist_cache, "w", encoding="utf-8") as f:
        f.write("aid\n")
        if unauthorized:
            f.write("<<Unauthorized>>\n")
            return
        for article in articlelist:
            f.write(f"{article.aid}\n")
