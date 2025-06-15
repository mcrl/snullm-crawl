import json
import http.client
import time
from logging import Logger
from typing import Any, Dict


from util.connection import get_html
from util.customexception import *


def read_err_message(message: Dict[str, Any]):
    err_message = message.get("message", None)
    if err_message is None:
        return ""
    code = err_message.get("code", None)
    msg = err_message.get("msg", None)
    if code is None or msg is None:
        return ""
    return f"code: {code}, msg: {msg}"


def get_response(
    uri: str,
    headers: Dict[str, Any],
    ip: str,
    logger: Logger,
    interval: int = 1,
    ignore_error: bool = False,
    field: str = "message",
):
    code, json_str = get_html(
        uri,
        headers,
        ip=ip,
        logger=logger,
        interval=interval,
        ignore_error=ignore_error,
        retry_interval=60,
    )
    # check if message has come
    if code == 429:
        msg = f"Too many requests via ip: {ip}"
        logger.critical(msg)
        raise TooManyRequestsError(msg)

    if json_str is None:
        msg = f"No response from {uri}"
        logger.critical(msg)
        raise NoResponseError(msg)

    # Check if json can be parsed
    try:
        message = json.loads(json_str).get(field, None)
    except:
        msg = f"Invalid response: {uri}"
        logger.error(msg)
        raise ResponseException(msg)

    if message is None:
        msg = f"Invalid response: {uri}"
        logger.error(msg)
        raise ResponseException(msg)

    if ignore_error:
        return message

    # Check json error code
    status = message.get("status", None)
    if status != "200":
        msg = f"Invalid response: {uri}"
        err_msg = read_err_message(message)
        if err_msg != "":
            msg += f", {err_msg}"
        logger.error(msg)
        raise ResponseException(msg)

    return message
