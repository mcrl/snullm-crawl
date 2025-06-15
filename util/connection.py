import time
from urllib.parse import urlparse
import gzip
import brotli
import http.client
from typing import Dict, Any, Optional
from logging import Logger

from util.customexception import TooManyRequestsError


def make_https_connection(netloc, ip=None):
    if ip:
        conn = http.client.HTTPSConnection(netloc, 443, source_address=(ip, 0))
    else:
        conn = http.client.HTTPSConnection(netloc, 443)
    return conn


def _get_html(
    uri: str,
    headers: Dict[str, Any],
    interval: int = 1,
    ignore_error: bool = False,
    ip: Optional[str] = None,
    logger: Optional[Logger] = None,
    verbose: bool = False,
    cookie_handler: Optional[callable] = None,
    error_override_function: Optional[callable] = None,
    retry_interval=15,
):
    def _handle_message(msg, logger, verbose):
        if logger:
            logger.info(msg)
        if verbose:
            print(msg)

    def _decode(resp):
        encoding = resp.getheader("Content-Encoding")
        if encoding == "gzip":
            return gzip.decompress(resp.read())
        if encoding == "br":
            return brotli.decompress(resp.read())
        return resp.read()

    def send_message(msg): return _handle_message(msg, logger, verbose)
    parsed = urlparse(uri)
    other_path = parsed.path + "?" + parsed.query

    for i in range(5):
        conn = None
        resp = None
        try:
            send_message(f"GET {uri}")
            conn = make_https_connection(parsed.netloc, ip)
            conn.request("GET", other_path, headers=headers)
            resp = conn.getresponse()
            headers["Referer"] = uri

            if resp.status == 302:
                href = resp.getheader("Location")
                return _get_html(
                    href,
                    headers,
                    interval=interval,
                    ignore_error=ignore_error,
                    ip=ip,
                    logger=logger,
                    verbose=verbose,
                    cookie_handler=cookie_handler,
                    retry_interval=retry_interval,
                )
            if resp.status == 429:
                if logger:
                    logger.critical("Too many requests")
                print("Too many requests")
                raise TooManyRequestsError

            if resp.status != 200:
                msg = f"GET {uri} failed: {resp.status}. Reason: {resp.reason}"
                if logger:
                    logger.error(msg)
                if logger is None and verbose:
                    print(msg)

                if error_override_function:
                    try:
                        data = _decode(resp).decode("utf-8", errors="ignore")
                    except:
                        data = None
                    if error_override_function(data):
                        msg = f"GET {uri} failed, yet override criteria is met"
                        logger.warning(msg)
                        return resp.status, data

                if ignore_error:
                    try:
                        data = _decode(resp)
                    except:
                        data = None
                    return resp.status, data

                time.sleep(retry_interval)
                retry_interval = retry_interval * 2
                continue

            try:
                cookie = resp.getheader("Set-Cookie")
            except:
                cookie = None
            if cookie:
                if cookie_handler:
                    new_cookie = cookie_handler(cookie)
                    headers["Cookie"] = new_cookie
                else:
                    headers["Cookie"] = cookie

            data = _decode(resp)
            return resp.status, data.decode("utf-8", errors="ignore")

        except Exception as e:
            logger.error("Failed to get %s: %s", uri, e)
            time.sleep(retry_interval)
            continue
    status = None
    data = None
    if resp:
        status = resp.status
        data = _decode(resp)
    logger.error("Too many errors have occured obtaining %s", uri)
    return status, data.decode("utf-8", errors="ignore")


def get_html(
    uri,
    headers,
    interval=1,
    ignore_error=False,
    ip=None,
    logger=None,
    verbose=False,
    cookie_handler=None,
    retry_interval=15,
    error_override_function=None,
):
    time.sleep(interval)
    return _get_html(
        uri,
        headers,
        interval=interval,
        ignore_error=ignore_error,
        logger=logger,
        verbose=verbose,
        ip=ip,
        cookie_handler=cookie_handler,
        retry_interval=retry_interval,
        error_override_function=error_override_function,
    )
