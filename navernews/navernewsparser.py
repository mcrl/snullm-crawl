from bs4 import BeautifulSoup, Comment
from io import StringIO
import time
import json
from datetime import datetime, timedelta
import re
from urllib import parse as urlparse
import os
import traceback
from util.crawler import fetch_html

IGNORE_NAMES = ["td", "script", "img", "caption"]
IGNORE_CLASSES = [
    ("em", "img_desc"),
    ("div", "categorize"),
    ("div", "reporter_area"),
    ("div", "copyright"),
]
comment_ptrn = re.compile("<!--.*?-->", re.DOTALL)


def get_article(contents, buf):
    for child in contents:
        if isinstance(child, str):
            if "MobileAdNew center" in child:
                continue
            buf.write(child.strip())
        elif child.name in IGNORE_NAMES:
            continue
        elif child.name == "br":
            buf.write("\n")
            if child.contents:
                get_article(child.contents, buf)
        else:
            get_article(child.contents, buf)


def find_text(soup, need_to_find=True):
    if need_to_find:
        tag = soup.select_one("#dic_area")
        if tag is None:
            tag = soup.select_one("#articeBody")
        if tag is None:
            tag = soup.select_one("#newsEndContents")
        if tag is None:
            tag = soup.select_one("#newsct_article")
        if tag is None:
            tag = soup.select_one("div._article_content")
    else:
        tag = soup

    for comments in tag.find_all(string=lambda string: isinstance(string, Comment)):
        comments.extract()
    for name, tag_class in IGNORE_CLASSES:
        tags = tag.find_all(name, class_=tag_class)
        if tags:
            for tg in tags:
                tg.extract()

    buf = StringIO()
    get_article(tag.contents, buf)
    text = buf.getvalue()
    buf.close()
    return text


def find_title(soup):
    meta_tag = soup.find("meta", attrs={"property": "og:title"})
    if meta_tag is None:
        return "notitle"
    content = meta_tag["content"]
    return content


def find_posttime(soup):
    time_format = "%Y-%m-%d %H:%M:%S"
    add_12hr = False
    tag = soup.find(
        "span", class_="media_end_head_info_datestamp_time _ARTICLE_DATE_TIME"
    )
    if tag:
        date_time = tag["data-date-time"]
    else:
        # sports
        selector = "#content > div > div.content > div > div.news_headline > div > span"
        tag = soup.select_one(selector)
        if tag is None:
            # entertainment
            selector = "#content > div.end_ct > div > div.article_info > span > em"
            tag = soup.select_one(selector)
        date_time = tag.text.strip()

        add_12hr = "오후" in date_time
        date_time = (
            date_time.replace("오후", "")
            .replace("오전", "")
            .replace(" ", "")
            .replace("기사입력", "")
        )
        time_format = "%Y.%m.%d.%H:%M"

    retrieved = datetime.strptime(date_time, time_format)
    if add_12hr:
        retrieved += timedelta(hours=12)
    formatted = retrieved.strftime("%Y-%m-%d")
    return formatted


def find_uri(soup):
    uri_tag = soup.find("meta", attrs={"property": "og:url"})
    if uri_tag:
        return uri_tag["content"]


def find_copyright(soup):
    copyright_tag = soup.select_one("p.c_text")
    if not copyright_tag:
        return ""
    return copyright_tag.text


def parse_navernews_soup(soup, logger, office, uri=None):
    # check if the article is deleted
    error_tags = [
        "div.error_msg",
        "div.error_page",
        "div.error_content",
    ]
    for selector in error_tags:
        tag = soup.select_one(selector)
        if tag:
            logger.warning(f"404 not found")
            return None
    try:
        payload = {}
        if uri is None:
            uri_tag = soup.find("meta", attrs={"property": "og:url"})
            uri = uri_tag["content"]
        payload["uri"] = uri
        payload["text"] = find_text(soup)
        # format 2018-10-16T22:32:13Z
        retrieval_date = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
        payload["retrieval_date"] = retrieval_date
        payload["type"] = "naver_news"
        payload["article_source"] = office
        payload["created_date"] = find_posttime(soup)
        payload["title"] = find_title(soup)
        payload["copyright"] = find_copyright(soup)
    except Exception as e:
        # print(e)
        # print traceback
        # print(traceback.format_exc())
        logger.error("parse_navernews_soup:Failed to parse %s", uri)
        return ""
    return json.dumps(payload, ensure_ascii=False)


def mobile_article_processing(real_uri, logger, office):
    # parse uri
    parsed = urlparse.urlparse(real_uri)
    host, path = parsed.netloc, parsed.path
    # mode: sports, entertain
    mode = host.split(".")[1]
    # oid, aid : last two elements of path
    oid, aid = path.split("/")[-2:]

    # cache path: data/navernews/{oid}/responses/{aid}.json
    cache_path = f"data/navernews/{oid}/responses/{aid}.json"
    if os.path.isfile(cache_path):
        json_entry = json.load(open(cache_path, "r"))
    else:
        # api uri: https://api-gw.sports.naver.com/news/article/055/0001143529
        api_uri = f"https://api-gw.{mode}.naver.com/news/article/{oid}/{aid}"
        json_resp = fetch_html(api_uri, logger, None)
        # save to cache
        with open(cache_path, "w") as f:
            f.write(json_resp)
        json_entry = json.loads(json_resp)

    result = json_entry["result"]
    info = result["articleInfo"]
    article = info["article"]
    payload = {}

    payload["uri"] = real_uri
    content = article["content"]
    payload["text"] = find_text(
        BeautifulSoup(content, "html.parser"), need_to_find=False
    )
    # format 2018-10-16T22:32:13Z
    retrieval_date = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    payload["retrieval_date"] = retrieval_date
    payload["type"] = "naver_news"
    payload["article_source"] = office

    service_datettime = article["serviceDatetime"]
    # format 2024-07-01 13:50:16 -> 2024-07-01
    payload["created_date"] = time.strftime(
        "%Y-%m-%d", time.strptime(service_datettime, "%Y-%m-%d %H:%M:%S")
    )
    payload["title"] = article["title"]
    payload["copyright"] = info["copyright"]
    return json.dumps(payload, ensure_ascii=False)


# m.sports.naver.com/article/119/0002845797
# m.entertain.naver.com/article/308/0000035102
# uri https://n.news.naver.com/mnews/article/057/0001827040?rc=N&ntype=RANKING


def handle_navernews_html(html, logger, office, uri=None, real_uri=None):
    def parse_uri(uri):
        # return oid, did
        tokens = uri.split("/")
        oid = tokens[5]
        did = tokens[6].split("?")[0]
        return oid, did

    if "/entertain.pstatic.net" in html:
        oid, did = parse_uri(uri)
        real_uri = f"https://m.entertain.naver.com/article/{oid}/{did}"
    elif "sports-phinf.pstatic.net" in html:
        oid, did = parse_uri(uri)
        real_uri = f"https://m.sports.naver.com/article/{oid}/{did}"
    if "m." in real_uri:
        return mobile_article_processing(real_uri, logger, office)
    html = comment_ptrn.sub("", html)
    soup = BeautifulSoup(html, "html.parser")
    return parse_navernews_soup(soup, logger, office, uri=uri)
