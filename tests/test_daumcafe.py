import pytest
from bs4 import BeautifulSoup
from daumcafe.structs import Article, Board, Cafe
from daumcafe.parser import (
    parse_article,
    is_erroneous_article,
    extract_board_info
)
from unittest.mock import Mock
from util.connection import get_html
from daumcafe.header import daumheader
from daumcafe.handler import peek_article, build_board_articlelist, build_cafe_boardlist, handle_article


@pytest.fixture
def dummy_logger():
    return Mock()

# https://m.cafe.daum.net/test34563


@pytest.fixture
def cafe():
    return Cafe(cafeid="test34563")


@pytest.fixture
def board(cafe):
    return Board(cafe=cafe, bid="WDZS", btype="normal", bname="Public Board")


@pytest.fixture
def memberonly_board(cafe):
    return Board(cafe=cafe, bid="WDZY", btype="normal", bname="Memberonly Board")


@pytest.fixture
def article(board):
    return Article(
        board=board,
        aid="1"
    )


@pytest.fixture
def memberonly_article(memberonly_board):
    return Article(
        board=memberonly_board,
        aid="1"
    )


def test_article_parsing(article):
    _, html = get_html(
        article.uri,
        daumheader
    )
    soup = BeautifulSoup(html, "html.parser")
    parse_article(article, soup, dummy_logger)
    assert article is not None
    assert article is not None
    assert article.text is not None
    assert article.title is not None
    assert article.uri is not None
    assert article.text.strip() == "text1"
    assert article.title.strip() == "title1"


def test_is_erroneous_article_public(article):
    _, html = get_html(
        article.uri,
        daumheader
    )
    soup = BeautifulSoup(html, "html.parser")
    assert is_erroneous_article(soup) == False


def test_is_erroneous_article_memberonly(memberonly_article, dummy_logger):
    _, html = get_html(
        memberonly_article.uri,
        daumheader,
        retry_interval=0.1,
        logger=dummy_logger
    )
    soup = BeautifulSoup(html, "html.parser")
    assert is_erroneous_article(soup) == True


def test_build_board_articlelist(board, dummy_logger):
    articles = build_board_articlelist(
        board,
        logger=dummy_logger,
        interval=0.1
    )
    assert len(articles) > 0
    assert all(isinstance(article, Article) for article in articles)


def test_board_info(board, dummy_logger):
    uri = f"https://m.cafe.daum.net/{board.cafe.cafeid}/{board.bid}"
    _, html = get_html(
        uri,
        daumheader,
        retry_interval=0.5,
        logger=dummy_logger
    )
    soup = BeautifulSoup(html, "html.parser")
    board_info = extract_board_info(soup)
    assert board_info is not None
    assert board_info["GRPID"] is not None
    assert board_info["FLDID"] is not None


def test_build_cafe_boardlist(cafe, dummy_logger):
    boards = build_cafe_boardlist(
        cafe,
        logger=dummy_logger,
        interval=0.5
    )
    assert len(boards) > 0
    assert all(isinstance(board, Board) for board in boards)
