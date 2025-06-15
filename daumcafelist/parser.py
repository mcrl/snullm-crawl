from bs4 import BeautifulSoup
from logging import Logger
from urllib.parse import urlparse
from typing import List, Tuple

from util.customexception import TooManyRequestsError


def find_cafeids(hrefs: List[str]) -> List[str]:
    def _href_to_cafeid(href: str) -> str:
        path = urlparse(href).path
        tokens = path.split("/")
        return tokens[1]

    return [
        _href_to_cafeid(href)
        for href in hrefs
        if href.startswith("https://m.cafe.daum.net/")
    ]


def is_blocked(soup: BeautifulSoup):
    test = "Are you a robot?"
    return test in soup.text


def acquire_search_results(
    soup: BeautifulSoup, logger: Logger
) -> Tuple[int, List[str]]:
    if is_blocked(soup):
        logger.critical("Blocked by Google")
        raise TooManyRequestsError

    selector = "#rso > div > div > div > div > div > div > span > a"
    tags = soup.select(selector)
    count = len(tags)
    if count == 0:
        logger.error("No search results")
    return count, find_cafeids([tag["href"] for tag in tags])
