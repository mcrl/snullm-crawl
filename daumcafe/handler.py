from logging import Logger
from typing import Dict, Any, List, Optional
import os.path as osp
from bs4 import BeautifulSoup
import multiprocessing as mp

import daumcafe.cache as dcache
from daumcafe.structs import Cafe, Board, Article
from daumcafe.header import daumheader
from daumcafe.parser import (
    parse_article,
    parse_cafe,
    find_sibling_pages,
    extract_single_page,
    check_next_page,
    is_erroneous_article,
    extract_board_info,
)
from daumcafe.checker import is_processed
from util.misc import get_interval
from util.connection import get_html
from urllib.parse import urlencode, urlunparse
import json


def build_board_uri(board_info, page=1) -> str:
    uri = f"https://m.cafe.daum.net/api/v1/common-articles?"
    params = {
        "grpid": board_info["GRPID"],
        "fldid": board_info["FLDID"],
        "targetPage": page,
        "pageSize": 20,
    }
    uri = urlunparse(
        (
            "https",
            "m.cafe.daum.net",
            "/api/v1/common-articles",
            "",
            urlencode(params),
            "",
        )
    )
    return uri


def override_article(html: str) -> bool:
    if html is None:
        return False
    try:
        soup = BeautifulSoup(html, "html.parser")
    except:
        return False
    return is_erroneous_article(soup)


def peek_article(article: Article, ip: str, logger: Logger, interval=1):
    _, html = get_html(
        article.uri,
        daumheader,
        interval=interval,
        ip=ip,
        logger=logger,
        ignore_error=True,
    )
    if html is None:
        logger.error("Failed to get %s", article.uri)
        return False
    try:
        soup = BeautifulSoup(html, "html.parser")
    except:
        return False
    if is_erroneous_article(soup):
        return False
    return True


def build_board_articlelist(
    board: Board, ip: Optional[str] = None, logger: Optional[Logger] = None, interval=1
) -> List[Article]:
    btype = board.btype
    if btype != "normal":
        logger.warning("Board %s is not normal board", board)
        return []

    accessible = False
    articles = []
    target_page = 1
    uri = f"https://m.cafe.daum.net/{board.cafe.cafeid}/{board.bid}"
    _, html = get_html(
        uri,
        daumheader,
        retry_interval=interval,
        logger=logger,
        ip=ip,
    )
    try:
        soup = BeautifulSoup(html, "html.parser")
        board_info = extract_board_info(soup)
    except Exception as e:
        msg = f"Failed to parse board_info from {uri}"
        logger.error(msg)
        return []
    uri = build_board_uri(board_info, page=target_page)
    while True:
        status, html = get_html(
            uri,
            daumheader,
            retry_interval=interval,
            ip=ip,
            logger=logger,
            ignore_error=not accessible,
        )
        if not accessible and status == 403:
            logger.warning("Board %s is not accessible", board)
            return []
        if html is None:
            return []
        try:
            data = json.loads(html)
            if 'code' in data and data['code'] == 0:
                break
            # soup = BeautifulSoup(html, "html.parser")
        except:
            msg = f"Failed to parse json from {uri}"
            logger.error(msg)
            return []
        # error check
        # selector = "#mArticle > div.cafe_error > h4.tit_error > span.txt_error"
        # tag = soup.select_one(selector)
        articles.extend(extract_single_page(data, board))

        if len(articles) == 0:
            logger.warning("Board %s is empty", board)
            return []

        if not accessible:
            trial_article = articles[0]
            if not peek_article(trial_article, ip, logger, interval=interval):
                logger.error(
                    "Failed to peek article %s. Member only", trial_article)
                return []
            accessible = True

        target_page += 1
        uri = build_board_uri(board_info, page=target_page)

    return articles


def build_cafe_boardlist(
    cafe: Cafe, ip: Optional[str] = None, logger: Optional[Logger] = None, interval=1
) -> List[Board]:
    referer_uri = f"https://m.cafe.daum.net/{cafe.cafeid}_rec?boardType=M"
    daumheader["Referer"] = referer_uri
    target_uri = f"https://m.cafe.daum.net/{cafe.cafeid}/"
    _, html = get_html(target_uri, daumheader,
                       interval=interval, ip=ip, logger=logger)
    if html is None:
        raise RuntimeError("Failed to get %s", target_uri)

    try:
        soup = BeautifulSoup(html, "html.parser")
    except:
        msg = f"Failed to parse html from {target_uri}"
        logger.error(msg)
        return []
    return parse_cafe(soup, cafe)


def handle_article(article: Article, ip: str, interval: int, logger: Logger):

    html = article.load_from_file()
    logger.info("Handling article %s", article)
    if html is None:
        _, html = get_html(
            article.uri,
            daumheader,
            interval=interval,
            ip=ip,
            logger=logger,
            error_override_function=override_article,
        )
        if html is None:
            logger.error("Article %s is not available", article.uri)
            return
        article.save_html(html)

    try:
        soup = BeautifulSoup(html, "html.parser")
    except Exception as e:
        msg = f"Failed to parse html from {article.uri}"
        logger.error(msg)
        return
    parse_article(article, soup, logger)


SKIP_WORDS = [
    "출석 체크",
    "출첵",
    "출석체크",
    "가입인사",
    "가입 인사",
    "등업",
    "신청",
    "승급",
]


def handle_board(
    board: Board, ip: str, interval: int, logger: Logger, save_queue: mp.Queue
):
    if is_processed(board):
        logger.warning("Board %s is already processed", board)
        return
    if board.btype != "normal":
        logger.warning("Board %s is not normal board", board)
        return

    bname = board.bname
    for word in SKIP_WORDS:
        if word in bname:
            logger.warning("Skipping Board %s: detected word %s", board, word)
            return

    logger.warning("Handling board %s", board)
    articlelist = dcache.read_board_cachefile(board)
    if articlelist is None:
        articlelist = build_board_articlelist(
            board, ip, logger, interval=interval)
        dcache.write_articlelist_cachefile(board, articlelist)
    else:
        logger.info(f"Read {len(articlelist)} articles from cache")

    ema = 1
    ratio = 0.1
    handled_consecutive = 0
    for article in articlelist:
        if article.is_downloaded():
            logger.info("Article %s is already handled", article)
            handled_consecutive += 1
            if handled_consecutive > 5:
                msg = f"The rest of the board {bname} seems to be handled"
                logger.warning(msg)
                break
            continue
        handled_consecutive = 0
        handle_article(article, ip, interval, logger)
        dump = article.to_json()
        if dump:
            save_queue.put(dump)
            ema = ema * (1 - ratio) + 1 * ratio
        else:
            ema = ema * (1 - ratio)
        if ema < 0.2:
            msg = f"Too many errors. Abort handling board {bname}"
            logger.error(msg)
            break


def handle_cafe(
    cafe: Cafe,
    shared_argv: Dict[str, Any],
    private_argv: Dict[str, Any],
    logger: Logger,
    save_queue=None,
):
    if is_processed(cafe):
        return
    # setup variables
    logger.warning("Handling cafe %s", cafe)
    ip = private_argv["ip"]
    interval = get_interval(shared_argv, private_argv)

    # if board list cachefile is available, use it.
    if osp.isfile(cafe.boardlist_cache):
        logger.info(f"Reading board list from {cafe.boardlist_cache}")
        boardlist = dcache.read_cafe_cachefile(cafe)
    else:
        boardlist = build_cafe_boardlist(cafe, ip, logger, interval=interval)
        dcache.write_cafe_cachefile(cafe, boardlist)

    # handle each boards
    for board in boardlist:
        handle_board(board, ip, interval, logger, save_queue)
