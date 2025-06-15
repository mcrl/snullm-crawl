import pytest
from bs4 import BeautifulSoup
from navernews.navernews_util import (
    read_cached_or_fetch_html,
    build_daylist,
)
from navernews.navernewsparser import parse_navernews_soup
import navernews.navernews_util
from unittest.mock import Mock
from util.env import get_iplist
from tests.mock import MockCache, MockResponse
import json
import util.crawler


@pytest.fixture
def dummy_logger():
    return Mock()


@pytest.fixture
def day():
    return "20230101"


@pytest.fixture
def oid():
    return "422"


@pytest.fixture
def ip():
    ips = get_iplist()
    print(f"Using IP: {ips[0]}")
    return ips[0]


@pytest.fixture
def article():
    return "https://n.news.naver.com/mnews/article/422/0000577235"


def test_build_daylist(day, oid, ip, dummy_logger):
    day_articles = build_daylist(
        day, oid, ip, dummy_logger, check_yesterday=False, save_cache=False)
    assert len(day_articles) > 0
    print(day_articles)
    assert all(article.startswith("https://n.news.naver.com/")
               for article in day_articles)


def test_fecth_and_parse_article(monkeypatch, article, dummy_logger, ip):
    monkeypatch.setattr(navernews.navernews_util,
                        "read_cached_html", MockCache.naver_read_cached_html)
    monkeypatch.setattr(navernews.navernews_util,
                        "save_html", MockCache.naver_save_html)
    monkeypatch.setattr(util.crawler, "fetch_html",
                        MockResponse.fetch_html)
    html, real_uri = read_cached_or_fetch_html(
        article, dummy_logger, ip, False)
    assert html is not None
    soup = BeautifulSoup(html, "lxml")
    parsed_text = parse_navernews_soup(soup, dummy_logger, "test_office")
    assert parsed_text is not None
    parsed = json.loads(parsed_text)
    assert parsed is not None
    assert len(parsed["text"]) > 100
    assert len(parsed["uri"]) > 10
    assert len(parsed["title"]) > 10
