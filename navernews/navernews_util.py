import os
from util.crawler import get_soup, fetch_html
from datetime import datetime, timedelta
import urllib.parse as urlparse


def read_cachefile(cache_path):
    with open(cache_path, "r") as f:
        lines = f.readlines()
    return [line.strip() for line in lines]


def write_cachefile(cache_path, data):
    with open(cache_path, "w") as f:
        f.write("\n".join(data))


def build_daylist(day, oid, ip, logger, check_yesterday=False, save_cache=True):
    def get_maxpage(day, oid, ip, conn=None):
        uri = f"https://news.naver.com/main/list.naver?mode=LPOD&mid=sec&oid={oid}&listType=title&date={day}&page=100"
        try:
            soup = get_soup(uri, logger, ip, conn=conn)
        except Exception as e:
            logger.error(f"Error in get_maxpage: {e}")
            return -1
        try:
            selector = "#main_content > div.paging > strong"
            tag = soup.select_one(selector)
            return int(tag.text)
        except Exception as e:
            logger.warning(f"Error in get_maxpage: {e}. Return -1.")
            return -1

    def get_page_articlelist(day, page, oid, ip, conn=None):
        uri = f"https://news.naver.com/main/list.naver?mode=LPOD&mid=sec&oid={oid}&listType=title&date={day}&page={page}"
        try:
            soup = get_soup(uri, logger, ip, conn=conn)
            selector = "#main_content > div.list_body.newsflash_body > ul > li > a"
            tags = soup.select(selector)
            article_list = [tag["href"] for tag in tags]
        except Exception as e:
            logger.error(f"Error in get_page_articlelist: {e}")
            return []
        return article_list

    cache_path = f"cache/navernews/{oid}/{day}.txt"
    if os.path.isfile(cache_path):
        return read_cachefile(cache_path)
    num_pages = get_maxpage(day, oid, ip)
    if num_pages == -1:
        return []
    article_list = []
    for page in range(1, num_pages + 1):
        article_list.extend(get_page_articlelist(day, page, oid, ip))

    if num_pages == 1 and check_yesterday:
        today = datetime.strptime(day, "%Y%m%d")
        yesterday = today - timedelta(days=1)
        yesterday = yesterday.strftime("%Y%m%d")
        yesterday_list = build_daylist(
            yesterday, oid, ip, logger, check_yesterday=False, save_cache=False
        )
        article_list = [
            article for article in article_list if article not in yesterday_list
        ]

    if save_cache:
        write_cachefile(cache_path, article_list)
    return article_list


def build_office_cachefile(path):
    # dir of path should be created before calling this function
    dir_path = os.path.dirname(path)
    if not os.path.isdir(dir_path):
        os.makedirs(dir_path)
    url = "https://news.naver.com/main/officeList.naver"
    soup = get_soup(url)
    selector = "#groupOfficeList > table > tbody > tr > td > ul > li > a"
    tags = soup.select(selector)
    with open(path, "w") as f:
        f.write("name\toid\n")
        for tag in tags:
            office_name = tag.text.strip()
            office_url = tag["href"]
            try:
                office_id = office_url.split("oid=")[1].split("&")[0]
            except:
                continue
            f.write(f"{office_name}\t{office_id}\n")


def build_office_dictionary(office_path=os.path.join("navernews", "offices.tsv")):
    if not os.path.isfile(office_path):
        build_office_cachefile(office_path)

    with open(office_path, "r") as f:
        lines = f.readlines()
    office_dict = {}
    for line in lines:
        if line.startswith("name"):
            continue
        name, oid = line.strip().split("\t")
        office_dict[name] = oid
    return office_dict


def parse_uri(uri):
    # case 1 https://n.news.naver.com/mnews/article/293/0000045707?rc=N&ntype=RANKING
    if uri.startswith("https://n.news.naver.com"):
        parsed = urlparse.urlparse(uri)
        oid = parsed.path.split("/")[3]
        idx = parsed.path.split("/")[4]
        return oid, idx
    # case 2 https://sports.naver.com/news?oid=032&aid=0003119852
    if uri.startswith("https://sports.naver.com"):
        parsed = urlparse.urlparse(uri)
        query_tokens = parsed.query.split("&")
        oid = query_tokens[0].split("=")[1]
        aid = query_tokens[1].split("=")[1]
        return oid, aid
    # case 3 https://entertain.naver.com/ranking/read?oid=396&aid=0000650302
    if uri.startswith("https://entertain.naver.com"):
        parsed = urlparse.urlparse(uri)
        query_tokens = parsed.query.split("&")
        oid = query_tokens[0].split("=")[1]
        aid = query_tokens[1].split("=")[1]
        return oid, aid

    return None, None


def html_save_path(oid, idx):
    return f"data/navernews/{oid}/htmls/{idx}.html"


def read_cached_html(oid, idx):
    path = html_save_path(oid, idx)
    try:
        if os.path.isfile(path):
            with open(path, "r") as f:
                return f.read()
        return None
    except:
        return None
    return None


def make_jsonl_savedir(oid):
    path = f"data/navernews/{oid}/jsonl"
    if not os.path.isdir(path):
        os.makedirs(path)


def jsonl_save_path(oid, day):
    return f"data/navernews/{oid}/jsonl/{day}.jsonl"


def save_html(oid, idx, html):
    path = html_save_path(oid, idx)
    with open(path, "w") as f:
        f.write(html)


def read_cached_or_fetch_html(uri, logger, ip, cache=True):
    oid, aid = parse_uri(uri)
    html = read_cached_html(oid, aid)
    if html:
        logger.info(f"Read cached html: {uri}")
        return html, uri
    result = fetch_html(uri, logger, ip, return_uri=True)
    if result is None:
        return None
    html, real_uri = result
    if html is None:
        return None
    if cache:
        save_html(oid, aid, html)
    return html, real_uri


def day_processed(day, oid):
    cache_path = f"cache/navernews/{oid}/{day}.txt"
    jsonl_path = jsonl_save_path(oid, day)

    if not os.path.isfile(cache_path):
        return False
    if not os.path.isfile(jsonl_path):
        return False

    # compare lines of two files
    try:
        with open(cache_path, "r") as f:
            cache_lines = f.readlines()
    except:
        # remove cache file
        os.remove(cache_path)
        return False

    try:
        with open(jsonl_path, "r") as f:
            jsonl_lines = f.readlines()
    except:
        os.remove(jsonl_path)
        return False

    # remove empty lines
    cache_lines = [line.strip() for line in cache_lines if line.strip()]
    jsonl_lines = [line.strip() for line in jsonl_lines if line.strip()]
    return len(cache_lines) == len(jsonl_lines)


def make_officedir(oid):
    cache_path = f"cache/navernews/{oid}"
    if not os.path.isdir(cache_path):
        os.makedirs(cache_path)
    done_path = f"cache/navernews/{oid}/done"
    if not os.path.isdir(done_path):
        os.makedirs(done_path)
    html_path = f"data/navernews/{oid}/htmls"
    if not os.path.isdir(html_path):
        os.makedirs(html_path)
    jsonl_path = f"data/navernews/{oid}/jsonl"
    if not os.path.isdir(jsonl_path):
        os.makedirs(jsonl_path)
    responses_path = f"data/navernews/{oid}/responses"
    if not os.path.isdir(responses_path):
        os.makedirs(responses_path)
