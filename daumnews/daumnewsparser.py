from bs4 import BeautifulSoup
from logging import Logger
from daumnews.article import dump_article
from io import StringIO
from datetime import datetime, timedelta


def get_article(contents: BeautifulSoup, buf: StringIO):
    for child in contents:
        if isinstance(child, str):
            buf.write(child.strip())
        elif child.name == "br":
            buf.write("\n")
            if child.contents:
                get_article(child.contents, buf)
        else:
            get_article(child.contents, buf)


def find_text(soup: BeautifulSoup):
    for table_tag in soup.find_all('table'):
        table_tag.decompose()

    for figure_tag in soup.find_all('figure'):
        figure_tag.decompose()

    tag = soup.select_one("div.news_view")
    buf = StringIO()
    get_article(tag.contents, buf)
    text = buf.getvalue()
    buf.close()
    return text


def find_uri(soup: BeautifulSoup):
    # get meta og:url
    url = soup.find("meta", attrs={"property": "og:url"})["content"]
    return url


def find_article_created(soup: BeautifulSoup):
    # get meta og:regDate
    date_time = soup.find("meta", attrs={"property": "og:regDate"})["content"]
    time_format = "%Y%m%d%H%M%S"
    retrieved = datetime.strptime(date_time, time_format)
    formatted = retrieved.strftime("%Y-%m-%d")
    return formatted


def find_title(soup: BeautifulSoup):
    # get meta og:title
    title = soup.find("meta", attrs={"property": "og:title"})["content"]
    return title


def parse_daumnews_soup(soup: BeautifulSoup, logger: Logger, office: str):
    error_tags = ["strong.tit_error"]

    for selector in error_tags:
        tag = soup.select_one(selector)
        if tag:
            logger.warning(f"Not found")
            return None

    cnt = 0
    try:
        text = find_text(soup)
        uri = find_uri(soup)
        created_date = find_article_created(soup)
        title = find_title(soup)
    except:
        logger.error("Error parsing")
        return None

    return dump_article(text, uri, "daum_news", office, created_date, title)
