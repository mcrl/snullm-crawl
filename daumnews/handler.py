import urllib.parse
from time import sleep
import gzip
import http.client
from bs4 import BeautifulSoup
import logging
import requests

HEADERS = {
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7",
    "Accept-Encoding": "gzip, deflate, br",
    "Accept-Language": "ko,en-US;q=0.9,en;q=0.8,ja;q=0.7",
    "Cookie": "__T_=1",
    "Referer": "https://https://news.daum.net/",
    "Sec-Ch-Ua": '"Not/A)Brand";v="99", "Google Chrome";v="115", "Chromium";v="115"',
    "Sec-Ch-Ua-Mobile": "?0",
    "Sec-Ch-Ua-Platform": "macOS",
    "Sec-Fetch-Dest": "document",
    "Sec-Fetch-Mode": "navigate",
    "Sec-Fetch-Site": "same-site",
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


def _fetch_html(uri, logger, ip, retry=5, retry_interval=15):
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
            retry_interval *= 1.5
        try:
            conn = make_conn(netloc, ip)
            logger.info("uri: " + str(uri) + ", retry: " + str(i))
            conn.request("GET", sendpath, headers=headers)
            resp = conn.getresponse()
            # headers["Referer"] = uri

            # handle redirection
            if resp.status == 302 and "Location" in resp.headers:
                html = fetch_html(resp.headers["Location"], logger, ip)
                return html

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

            # cookie = resp.getheader("Set-Cookie")
            # if cookie:
            #    headers["Cookie"] = cookie[: cookie.find(";")]

            encoding = resp.getheader("Content-Encoding")
            if encoding == "gzip":
                data = gzip.decompress(resp.read())
            else:
                data = resp.read()
            return data.decode("utf-8", errors="ignore")
        except Exception as e:
            logger.error(f"Exception: {e}, uri: {uri}, retry: {i}")
    logger.critical(f"Failed to fetch {uri}, retry: {retry} times")
    raise Exception(f"Failed to fetch {uri}, retry: {retry} times")


def fetch_html(uri, logger, ip=None, retry=5, interval=0.7, retry_interval=15):
    sleep(interval)
    return _fetch_html(uri, logger, ip, retry=retry, retry_interval=retry_interval)


def get_soup(uri, logger=None, ip=None, conn=None, interval=0.7):
    sleep(interval)
    data = fetch_html(uri, logger, ip)
    if data is None:
        return None
    soup = BeautifulSoup(data, "lxml")
    return soup


def fetch_json(uri, body, logger, ip=None, retry=5, interval=0.7, retry_interval=15):
    sleep(interval)
    return _fetch_json(uri, body, logger, ip, retry=retry, retry_interval=retry_interval)


def _fetch_json(uri, body, logger, ip, retry=5, retry_interval=15):
    if logger is None:
        logger = logging.getLogger(__name__)
    headers = HEADERS
    headers["Content-Type"] = "application/json"
    for i in range(retry):
        try:
            if i > 0:
                sleep(retry_interval)
                retry_interval *= 1.5
            response = requests.post(uri, headers=headers, json=body)
            if response.status_code == 200:
                return response.json()
            else:
                logger.error(
                    f"Failed to fetch {uri}, retry: {i}, status: {response.status_code}")

            if response.status == 404:
                logger.error(
                    f"status: {response.status}, reason: {response.reason} uri: {uri}")
                return None

            if response.status == 403:
                logger.critical("Possible IP ban %s", ip)
                raise Exception(f"Possible IP ban {ip}")

            if response.status != 200:
                logger.error(
                    f"status: {response.status}, reason: {response.reason} uri: {uri}")
                continue
            return response.json()
        except Exception as e:
            logger.error(f"Exception: {e}, uri: {uri}, retry: {i}")
    logger.critical(f"Failed to fetch {uri}, retry: {retry} times")
    raise Exception(f"Failed to fetch {uri}, retry: {retry} times")
