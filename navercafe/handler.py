from logging import Logger
from typing import Dict, Any, List, Tuple, Optional
import datetime
from bs4 import BeautifulSoup
import json
from io import StringIO
import os.path as osp
import multiprocessing as mp
import re

import navercafe.cache as ncache
from navercafe.structs import Cafe, Board, Article
from navercafe.header import ncafeheader
import navercafe.checker as nchecker
from navercafe.json_util import get_response

from util.misc import get_interval
from util.customexception import *
from util.ema import Ema

IGNORES = [
    "SE-TEXT",
    "SE_DOC_HEADER_START",
    "SE_DOC_HEADER_END",
    "@CONTENTS_HEADER",
    "CONTENT-ELEMENT",
    "!supportEmptyParas",
    "![endif]",
    "@CUSTOM",
    "[data-hwpjson]",
]

BANNED_CLASSES = [r'"hwp_editor_board_content"']
BANNED_IDS = [r'"SL_locer"', '"SL_BBL_locer"']


def ignore_tag(line):
    for ignore in IGNORES:
        if ignore in line:
            return True
    return False


def recursive_text(tag, buf):
    # check class
    if isinstance(tag, str):
        if ignore_tag(tag):
            return
        buf.write(tag)
        return
    try:
        tag_class = tag.get("class")
        if tag_class in BANNED_CLASSES:
            return
    except:
        pass

    try:
        tag_id = tag.get("id")
        if tag_id in BANNED_IDS:
            return
    except:
        pass

    if tag.name == "br":
        buf.write("\n")

    contents = tag.contents
    if not contents:
        return
    for child in contents:
        recursive_text(child, buf)


def extract_text(given_html: str) -> str:
    soup = BeautifulSoup(given_html, "html.parser")
    buf = StringIO()
    recursive_text(soup, buf)
    text = buf.getvalue().strip()
    # replace multiple consecutive newlines with one newline
    text = re.sub(r"\n+", "\n", text)
    return text


def get_article_json(article: Article, ip: str, logger: Logger, interval: int = 1):
    iid = article.board.cafe.cafe_internalid
    mid = article.board.bid
    aid = article.aid
    url = f"https://apis.naver.com/cafe-web/cafe-articleapi/v2.1/cafes/{iid}/articles/{aid}?menuId={mid}&tc=cafe_article_list&useCafeId=true"

    referer = f"https://m.cafe.naver.com/ca-fe/web/cafes/{iid}/articles/{aid}?fromList=true&menuId={mid}&tc=cafe_article_list"
    ncafeheader["Referer"] = referer
    try:
        logger.info(f"get article json : referer: {referer}")
        json_message = get_response(
            url,
            ncafeheader,
            interval=interval,
            ip=ip,
            logger=logger,
            field="result",
            ignore_error=True,
        )
    except TooManyRequestsError as tmre:
        msg = f"Too many requests for {article}"
        logger.critical(msg)
        raise tmre
    except Exception as e:
        msg = f"Failed to get response for {article}, Exception: {e}"
        logger.error(msg)
        return None
    article.write_json(json_message)
    return json_message


def set_article(
    article: Article, ip: str, logger: Logger, interval: int = 1
) -> Optional[Article]:
    if article.is_processed():
        msg = f"Article {article} is already processed"
        logger.warning(msg)
        return None

    json_message = get_article_json(article, ip, logger, interval=interval)
    if json_message is None:
        msg = f"Failed to get article json for {article}"
        logger.error(msg)
        return None

    try:
        article_html = json_message["article"]["contentHtml"]

        posted_time = json_message["article"]["writeDate"] / 1000
        dt_object = datetime.datetime.fromtimestamp(posted_time)

        comments = json_message["comments"]["items"]
        comment_texts = [comment["content"] for comment in comments]
        comment_text = "\n".join(comment_texts)

        article.title = json_message["article"]["subject"]
        article.retrieved = datetime.datetime.now().strftime("%Y-%m-%dT%H:%M:%SZ")
        article.text = extract_text(article_html) + "\n" + comment_text
        article.posted = dt_object.strftime("%Y-%m-%d")
        return article

    except Exception as e:
        msg = f"Failed to parse article {article}, Exception: {e}"
        logger.error(msg)
        return None


def handle_page(
    board: Board,
    page_entry: Dict[str, Any],
    ip: str,
    logger: Logger,
    interval: int,
    save_queue: mp.Queue,
):
    ema = Ema(10)
    articles = page_entry.get("articles", [])
    for aid in articles:
        article = Article(board, aid)
        result = set_article(article, ip, logger, interval=interval)
        if result:
            save_queue.put(result.to_json())
            ema.update(len(result.text) > 10)
        else:
            ema.update(False)
        if ema.value < 0.15:
            return False
    return True


def can_read_article(entry: Dict[str, Any]) -> bool:
    blindArticle = entry.get("blindArticle", True)
    openArticle = entry.get("openArticle", False)
    return not blindArticle and openArticle


def get_page_json(board: Board, page: int, ip: str, logger: Logger, interval: int = 1):
    host = "apis.naver.com"
    path = "/cafe-web/cafe2/ArticleListV2dot1.json"
    bid = board.bid
    internalid = board.cafe.cafe_internalid
    query = f"search.clubid={internalid}&search.queryType=lastArticle&search.menuid={bid}&search.page={page}&search.perPage=50"

    url = f"https://{host}{path}?{query}"
    referer = f"https://m.cafe.naver.com/ca-fe/web/cafes/{internalid}/menus/{bid}"
    ncafeheader["Referer"] = referer

    try:
        return get_response(url, ncafeheader, interval=interval, ip=ip, logger=logger)
    except TooManyRequestsError as tmre:
        msg = f"Too many requests for {board}"
        logger.critical(msg)
        raise tmre
    except Exception as e:
        msg = f"Failed to get response for {board}, Exception: {e}"
        logger.error(msg)
        return None


def build_page_entries(
    board: Board, page_num: int, ip: str, logger: Logger, interval: int = 1
) -> Tuple[List[str], bool]:
    json_message = get_page_json(
        board, page_num, ip, logger, interval=interval)
    if json_message is None:
        return None, None

    new_list = []
    try:
        has_next = json_message["result"]["hasNext"]
        article_list = json_message["result"]["articleList"]
    except Exception as e:
        msg = f"Failed to get article list for {board}, Exception: {e}"
        logger.error(msg)
        return None, None

    for entry in article_list:
        if not can_read_article(entry):
            continue
        articleId = str(entry["articleId"])
        new_list.append(articleId)

    return new_list, has_next


def check_board_memberonly(
    board: Board, ip: str, logger: Logger, interval: int = 1
) -> bool:
    """
    Checks if the board article is accessible to ordinary user.
    We check the most recent page of the board, and regard 'accessible' if more than 10% of articles are accessible
    """

    message = get_page_json(board, 1, ip, logger, interval=interval)
    if message is None:
        raise Exception(f"Failed to get page 1 for {board}")

    try:
        articles = message["result"]["articleList"]
    except Exception as e:
        msg = f"Failed to get article list for {board}, Exception: {e}"
        logger.error(msg)
        return None

    accessible_count = 0
    total_count = 0
    for article in articles:
        total_count += 1
        if can_read_article(article):
            accessible_count += 1
    if accessible_count == 0:
        return True
    return accessible_count / total_count < 0.1


def handle_board(
    board: Board,
    ip: str,
    logger: Logger,
    interval: int = 1,
    save_queue: mp.Queue = None,
):
    if save_queue is None:
        raise ValueError("save_queue is None")
    msg = f"Handling board {board}"
    logger.warning(msg)
    board_status = ncache.read_cache(board)

    member_only = board_status.get("member_only")
    if member_only is None:
        member_only = check_board_memberonly(
            board, ip, logger, interval=interval)
        board_status["member_only"] = member_only
        ncache.write_cache(board, board_status)

    if member_only:
        msg = f"Board {board} is member only. Skip"
        logger.warning(msg)
        nchecker.mark_done(board_status)
        ncache.write_cache(board, board_status)
        return

    # fetch cached page
    pages = board_status.get("pages", [])

    # if rebuild is needed, rebuild the page
    need_rebuild = nchecker.duration_passed(board_status)
    is_processed = nchecker.check_done(board_status)
    if need_rebuild:
        pages = []
        logger.warning("Rebuilding board %s", board)
        ncache.write_cache(board, board_status)
    elif is_processed:
        msg = f"Board {board} is already processed"
        logger.warning(msg)
    board_status["pages"] = pages

    page = 1
    if len(pages) > 0:
        for cached_page in pages:
            page += 1
            if page > 1000:
                # This seems useless, yet some cachefile has page > 1000
                # These cache files hold faulty data, so we skip them
                break
            done = cached_page.get("done", False)
            if done:
                logger.info("Page %d is already processed", page)
                continue
            handle_page(board, cached_page, ip, logger, interval, save_queue)
            cached_page["done"] = True
            ncache.write_cache(board, board_status)

    has_next = True
    while has_next:
        if page > 1000:
            break  # naver cafe allows only 1000 pages of articles
        try:
            page_entry = {}
            pages.append(page_entry)
            article_entries, has_next = build_page_entries(
                board, page, ip, logger, interval
            )
            if article_entries is None:
                return
            page_entry["page"] = page
            page_entry["articles"] = article_entries
            ncache.write_cache(board, board_status)
            res = handle_page(board, page_entry, ip,
                              logger, interval, save_queue)
            page_entry["done"] = True
            ncache.write_cache(board, board_status)
            page += 1
            if not res:
                logger.warning("Board %s seems to contain empty pages", board)
                break
        except Exception as e:
            msg = f"Failed to fetch page {page} for {board}, Exception: {e}"
            logger.error(msg)
            return

    nchecker.mark_done(board_status)
    ncache.write_cache(board, board_status)


SKIP_WORDS = [
    "출석 체크",
    "출첵",
    "출석체크",
    "가입인사",
    "가입 인사",
    "등업",
    "신청",
    "출석",
]


def get_cafe_boardlist(
    cafe: Cafe, ip: str, logger: Logger, interval: int = 1
) -> List[Dict[str, str]]:
    internalid = cafe.cafe_internalid
    url = f"https://apis.naver.com/cafe-web/cafe2/SideMenuList?cafeId={internalid}"
    referer = f"https://m.cafe.naver.com/ca-fe/{cafe.cafeid}"
    ncafeheader["Referer"] = referer

    try:
        json_message = get_response(
            url, ncafeheader, interval=interval, ip=ip, logger=logger
        )
    except TooManyRequestsError as tmre:
        msg = f"Too many requests for {cafe.cafeid}"
        logger.critical(msg)
        raise tmre
    except Exception as e:
        msg = f"Failed to get response for {cafe.cafeid}, Exception: {e}"
        logger.error(msg)
        return None

    try:
        menus = json_message["result"]["menus"]
    except Exception as e:
        msg = f"Failed to get boardlist for {cafe.cafeid}, Exception: {e}"
        logger.error(msg)
        return None

    boardlist = []
    for menu in menus:
        # Check if the menu is a board
        skip = False
        menuType = menu.get("menuType", None)
        boardType = menu.get("boardType", None)
        menuName = menu["menuName"]

        if menuType != "B" or boardType != "L":
            msg = f"Menu {menuName} is not a board"
            logger.info(msg)
            continue
        for skip_word in SKIP_WORDS:
            if skip_word in menuName:
                msg = (
                    f"Menu {menuName} is skipped. Skip word {skip_word} is in the name"
                )
                logger.info(msg)
                skip = True
        if skip:
            continue

        menuid = menu["menuId"]
        item = {"bid": str(menuid), "bname": str(menuName)}
        boardlist.append(item)
    return boardlist


def get_cafe_internalid(cafe: Cafe, ip: str, logger: Logger, interval: int = 1) -> int:
    cafeid = cafe.cafeid
    url = f"https://apis.naver.com/cafe-web/cafe2/CafeGateInfo.json?cluburl={cafeid}"
    referer = f"https://m.cafe.naver.com/ca-fe/{cafe.cafeid}"
    ncafeheader["Referer"] = referer

    try:
        message = get_response(
            url, ncafeheader, interval=interval, ip=ip, logger=logger
        )
    except TooManyRequestsError as tmre:
        msg = f"Too many requests for {cafeid}"
        logger.critical(msg)
        raise tmre
    except Exception as e:
        msg = f"Failed to get response for {cafeid}, Exception: {e}"
        logger.error(msg)
        return None
    try:
        cafeId = message["result"]["cafeInfoView"]["cafeId"]
    except:
        msg = f"Failed to get cafeid for {cafeid}. No cafeId in result"
        logger.error(msg)
        return None
    return str(cafeId)


def handle_cafe(
    cafe: Cafe,
    shared_argv: Dict[str, Any],
    private_argv: Dict[str, Any],
    logger: Logger,
    save_queue: Optional[mp.Queue] = None,
):
    if nchecker.is_processed(cafe):
        logger.warning("Skipping cafe %s", cafe)
        return
    # setup variables
    logger.warning("Handling cafe %s", cafe)
    ip = private_argv["ip"]
    interval = get_interval(shared_argv, private_argv)
    cafe_status = ncache.read_cache(cafe)
    cafe_status["cafeid"] = cafe.cafeid

    # get cafeid, cafeinternalid
    cafe.cafe_internalid = cafe_status.get("cafe_internalid")
    if cafe.cafe_internalid is None:
        cafe.cafe_internalid = get_cafe_internalid(
            cafe, ip, logger, interval=interval)
        if cafe.cafe_internalid is None:
            return
        cafe_status["cafe_internalid"] = cafe.cafe_internalid
        ncache.write_cache(cafe, cafe_status)

    # if board list cachefile is available, use it.
    boards = cafe_status.get("boards")
    if boards is None:
        boards = get_cafe_boardlist(cafe, ip, logger, interval=interval)
        if boards:
            cafe_status["boards"] = boards
            ncache.write_cache(cafe, cafe_status)
    if boards is None:
        logger.error("Failed to get boardlist for %s", cafe)
        return

    # handle each boards
    for entry in boards:
        board = Board(cafe, entry["bid"], entry["bname"])
        handle_board(board, ip, logger, interval=interval,
                     save_queue=save_queue)

    nchecker.mark_done(cafe_status)
    ncache.write_cache(cafe, cafe_status)
