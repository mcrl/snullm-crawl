import pytest
from bs4 import BeautifulSoup
from daumnews.daumnews_util import (
    read_cached_or_fetch_html,
)
from daumnews.daumnewsparser import parse_daumnews_soup
from unittest.mock import Mock
from util.env import get_iplist
from tests.mock import MockCache, MockResponse
import json
import daumnews.daumnews_util
import daumnews.handler


@pytest.fixture
def dummy_logger():
    return Mock()


@pytest.fixture
def day():
    return "20230101"


@pytest.fixture
def oid():
    return 23


@pytest.fixture
def ip():
    ips = get_iplist()
    print(f"Using IP: {ips[0]}")
    return ips[0]


@pytest.fixture
def article():
    return "https://v.daum.net/v/20230101234115402"


def test_fecth_and_parse_article(monkeypatch, article, dummy_logger, ip):
    monkeypatch.setattr(daumnews.daumnews_util,
                        "read_cached_html", MockCache.read_cached_html)
    monkeypatch.setattr(daumnews.daumnews_util,
                        "save_html", MockCache.daum_save_html)
    monkeypatch.setattr(daumnews.handler, "fetch_html",
                        MockResponse.fetch_html)
    html = read_cached_or_fetch_html(article, dummy_logger, ip, False)
    assert html is not None
    soup = BeautifulSoup(html, "lxml")
    parsed_text = parse_daumnews_soup(soup, dummy_logger, "test_office")
    assert parsed_text is not None
    parsed = json.loads(parsed_text)
    assert parsed is not None
    assert len(parsed["text"]) > 100
    assert len(parsed["article_title"]) > 10
    assert len(parsed["uri"]) > 10
