import urllib.parse
from time import sleep
import gzip
import http.client
from bs4 import BeautifulSoup
import logging
from io import BytesIO
HEADERS = {
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7",
    "Accept-Encoding": "gzip, deflate, br",
    "Accept-Language": "ko,en-US;q=0.9,en;q=0.8,ja;q=0.7",
    "Cookie": "",
    "Referer": "https://news.naver.com/main/officeList.naver",
    "Sec-Ch-Ua": '"Not.A/Brand";v="8", "Chromium";v="114", "Google Chrome";v="114"',
    "Sec-Ch-Ua-Mobile": "?0",
    "Sec-Ch-Ua-Platform": "macOS",
    "Sec-Fetch-Dest": "document",
    "Sec-Fetch-Mode": "navigate",
    "Sec-Fetch-Site": "same-origin",
    "Sec-Fetch-User": "?1",
    "Upgrade-Insecure-Requests": "1",
    "user-agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/114.0.0.0 Safari/537.36",
}


def make_conn(netloc, ip):
    if ip:
        conn = http.client.HTTPSConnection(netloc, 443, source_address=(ip, 0))
    else:
        conn = http.client.HTTPSConnection(netloc, 443)
    return conn


def _fetch_html(uri, logger, ip, retry=5, retry_interval=30, return_uri=False):
    if logger is None:
        logger = logging.getLogger(__name__)
    parsed_uri = urllib.parse.urlparse(uri)
    path = parsed_uri.path
    query = parsed_uri.query
    netloc = parsed_uri.netloc
    sendpath = path + "?" + query
    headers = HEADERS

    for i in range(retry):
        conn = None
        resp = None
        if i > 0:
            sleep(retry_interval)
            retry_interval *= 2
        try:
            conn = make_conn(netloc, ip)
            logger.info(f"uri: {uri}, retry: {i}")
            conn.request("GET", sendpath, headers=headers)
            resp = conn.getresponse()
            headers["Referer"] = uri

            # handle redirection
            if resp.status == 302 and "Location" in resp.headers:
                res = fetch_html(
                    resp.headers["Location"], logger, ip, return_uri=return_uri
                )
                return res

            # check status
            if resp.status == 404:
                logger.error(
                    f"status: {resp.status}, reason: {resp.reason} uri: {uri}")
                return None
            if resp.status == 403:
                logger.critical("Possible IP ban %s", ip)
                raise Exception(f"Possible IP ban {ip}")

            if resp.status != 200:
                logger.error(
                    f"status: {resp.status}, reason: {resp.reason} uri: {uri}")
                continue

            cookie = resp.getheader("Set-Cookie")
            if cookie:
                headers["Cookie"] = cookie[: cookie.find(";")]

            encoding = resp.getheader("Content-Encoding")
            if encoding == "gzip":
                raw = resp.read()
                charset = resp.getheader("Content-Type").split("charset=")
                buf = BytesIO(raw)
                with gzip.GzipFile(fileobj=buf) as f:
                    resp_charset = charset[1] if len(charset) > 1 else "utf-8"
                    data = f.read().decode(resp_charset, errors="ignore")
                return data, uri
            else:
                data = resp.read()
            return data.decode("utf-8", errors="ignore"), uri
        except Exception as e:
            logger.error(f"Exception: {e}, uri: {uri}, retry: {i}")
    return None


def fetch_html(
    uri, logger, ip=None, retry=5, interval=0.75, retry_interval=15, return_uri=False
):
    sleep(interval)
    res = _fetch_html(
        uri,
        logger,
        ip,
        retry=retry,
        retry_interval=retry_interval,
        return_uri=return_uri,
    )
    if res is None:
        return res
    if return_uri:
        return res
    return res[0]


def get_soup(uri, logger=None, ip=None, conn=None, interval=1):
    sleep(interval)
    data = fetch_html(uri, logger, ip)
    if data is None:
        return None
    try:
        soup = BeautifulSoup(data, "lxml")
    except:
        return None
    return soup
