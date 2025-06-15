from bs4 import BeautifulSoup
from logging import Logger
from io import StringIO
from datetime import datetime
from daumcafe.structs import Article, Board, Cafe
import json
import re
"""
Section for parsing single article
"""


def iterate_article_paragraphs(soup: BeautifulSoup, buf: StringIO):
    selector = "p"
    tags = soup.select(selector)
    for tag in tags:
        buf.write(tag.text)
        buf.write("\n")


def is_memberonly(soup: BeautifulSoup):
    selector = "#mArticle > h3.sr_only"
    tag = soup.select_one(selector)
    return tag is not None


def is_erroneous_article(soup: BeautifulSoup):
    check_functions = [is_memberonly]
    for check_function in check_functions:
        if check_function(soup):
            return True
    return False


def parse_article_content(soup: BeautifulSoup, logger: Logger):
    # get article text
    selector = "#article"
    tag = soup.select_one(selector)
    if tag is None:
        logger.error("Failed to find article content")
        return None
    buf = StringIO()
    iterate_article_paragraphs(tag, buf)
    return buf.getvalue()


def parse_posted_time(soup: BeautifulSoup, logger: Logger):
    selector = "#mArticle > div.view_subject > span.txt_subject > span.num_subject"
    tag = soup.select_one(selector)
    if tag is None:
        return "1900-01-01"
    text = tag.text

    if ":" in text or "전" in text:
        return datetime.today().strftime("%Y-%m-%d")
    # format yy.mm.dd into yyyy-mm-dd
    return f"20{text.replace('.', '-')}"


def parse_article(article: Article, soup: BeautifulSoup, logger: Logger):
    if is_erroneous_article(soup):
        logger.error("Article %s is erroneous", article.uri)
        return
    try:
        article.text = parse_article_content(soup, logger)
        article.title = soup.select_one("meta[property='og:title']")["content"]
        article.posted = parse_posted_time(soup, logger)
        article.retrieved = datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")
    except:
        logger.error("Failed to parse article %s", article.uri)
        article.text = None


"""
Section for generating board list
"""


def parse_cafe(soup: BeautifulSoup, cafe: Cafe):
    def _parse_tag(tag: BeautifulSoup, cafe: Cafe):
        subtag_selector = " strong > span"
        subtag = tag.select_one(subtag_selector)
        href = tag["href"]
        cafeid = cafe.cafeid
        if not href.startswith(f"/{cafeid}/"):
            return Board(cafe, "unknown", "unknown", subtag.text)

        board_token = href.split("/")[-1]
        btokens = board_token.split("?")
        if len(btokens) != 2:
            return Board(cafe, "unknown", "unknown", subtag.text)
        bid, btype = btokens[0], btokens[1]
        if btype.endswith("="):
            btype = "normal"
        else:
            btype = btype[-1:]
        return Board(cafe, bid, btype, subtag.text)

    selector = "#boardList > li > a"
    tags = soup.select(selector)
    return [_parse_tag(tag, cafe) for tag in tags]


"""
Section for generating article list
"""


def find_sibling_pages(soup: BeautifulSoup):
    selector = "#pagingNav > span > a.link_page"
    tags = soup.select(selector)
    return [tag["href"] for tag in tags]


def build_board_uri(board_info) -> str:
    uri = f"https://m.cafe.daum.net/api/v1/common-articles?"
    params = {
        "grpid": board_info["GRPID"],
        "fldid": board_info["FLDID"],
        "targetPage": 1,
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


def build_article(article_data, board) -> str:
    return Article(board, str(article_data['dataid']))


def extract_single_page(data, board: Board):
    return [build_article(article, board) for article in data['articles']]


# def extract_single_page(soup: BeautifulSoup, board: Board):
#     def _href_to_article(href, board):
#         aid = href.split("/")[-1]
#         return Article(board, aid)

#     selector = "#slideArticleList > ul > li > a.link_cafe.make-list-uri.\#article_list"
#     tags = soup.select(selector)
#     return [_href_to_article(tag["href"], board) for tag in tags]


def check_next_page(soup: BeautifulSoup):
    selector = "#mArticle > div.paging_board > a.btn_page.btn_next"
    tag = soup.select_one(selector)
    if tag is None:
        return None
    href = tag["href"]
    if "#" in href or "none" in href:
        return None
    return href


def extract_board_info(soup: BeautifulSoup):
    # 1. Find the <script> that contains the CAFEAPP definition
    script = soup.find("script", string=re.compile(r"var\s+CAFEAPP"))
    js = script.string
    # 2. Extract just the object literal
    m = re.search(r"var\s+CAFEAPP\s*=\s*({.*?});", js, re.S)
    obj_text = m.group(1)
    # 3. Turn it into JSON:
    json_text = re.sub(
        r'(?<=[{,])\s*([A-Za-z_]\w*)\s*:',
        r'"\1":',
        obj_text
    )
    json_text = json_text.replace("'", '"')
    control_char_re = re.compile(
        r'(?<!\\)[\x00-\x08\x0b\x0c\x0e-\x1f]'
    )
    json_text = control_char_re.sub('', json_text)
    data = json.loads(json_text)
    return data
