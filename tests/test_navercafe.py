import pytest
from navercafe.structs import Article, Board, Cafe
from navercafe.handler import (
    get_article_json,
    build_page_entries,
    check_board_memberonly,
    get_cafe_boardlist,
    set_article
)
from unittest.mock import Mock
from util.env import get_iplist
import navercafe.structs
import os


@pytest.fixture(autouse=True)
def no_makedirs(monkeypatch):
    monkeypatch.setattr(os, "makedirs", lambda path, exist_ok=True: None)
    yield


@pytest.fixture(autouse=True)
def no_write_json(monkeypatch):
    monkeypatch.setattr(navercafe.structs.Article,
                        "write_json", lambda *args, **kwargs: None)
    yield


@pytest.fixture
def dummy_logger():
    return Mock()

# https://cafe.naver.com/test34563


@pytest.fixture
def cafe():
    cafe = Cafe(cafeid="test34563")
    cafe.cafe_internalid = "31472959"
    return cafe


@pytest.fixture
def board(cafe):
    return Board(cafe=cafe, bid="1", bname="Public Board")


@pytest.fixture
def memberonly_board(cafe):
    return Board(cafe=cafe, bid="2", bname="Memberonly Board")


@pytest.fixture
def article(board):
    return Article(
        board=board,
        aid="3"
    )


@pytest.fixture
def ip():
    ips = get_iplist()
    print(f"Using IP: {ips[0]}")
    return ips[0]


@pytest.fixture
def memberonly_article(memberonly_board):
    return Article(
        board=memberonly_board,
        aid="3"
    )


def test_check_board_memberonly_false(board, dummy_logger, ip):
    result = check_board_memberonly(board, ip=ip, logger=dummy_logger)
    assert result is False


def test_check_board_memberonly_true(memberonly_board, dummy_logger, ip):
    result = check_board_memberonly(
        memberonly_board, ip=ip, logger=dummy_logger)
    assert result is True


def test_get_cafe_boardlist(cafe, ip, dummy_logger):
    boards = get_cafe_boardlist(cafe, ip=ip, logger=dummy_logger)
    assert len(boards) > 0


def test_build_page_entries(board, ip,  dummy_logger):
    article_ids, has_next = build_page_entries(
        board,
        page_num=1,
        ip=ip,
        logger=dummy_logger,
        interval=0.5
    )
    assert len(article_ids) > 0


def test_set_article(article, ip, dummy_logger):
    article_obj = set_article(article, ip=ip, logger=dummy_logger, interval=1)
    assert article_obj is not None
    assert article_obj.title is not None
    assert article_obj.text is not None


def test_article_parsing(article, ip, dummy_logger):
    data = get_article_json(article, ip, dummy_logger, interval=1)
    assert data is not None
