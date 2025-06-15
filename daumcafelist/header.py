import re
from io import StringIO

googleheader = {
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7",
    "Accept-Encoding": "gzip, deflate, br",
    "Accept-Language": "ko",
    "Sec-Ch-Ua": '"Not.A/Brand";v="8", "Chromium";v="114", "Google Chrome";v="114"',
    "Sec-Ch-Ua-Arch": "arm",
    "Sec-Ch-Ua-Bitness": "64",
    "Sec-Ch-Ua-Full-Version-List": '"Not.A/Brand";v="8.0.0.0", "Chromium";v="114.0.5735.198", "Google Chrome";v="114.0.5735.198"',
    "Sec-Ch-Ua-Mobile": "?0",
    "Sec-Ch-Ua-Model": "",
    "Sec-Ch-Ua-Platform": "macOS",
    "Sec-Ch-Ua-Platform-Version": "12.2.1",
    "Sec-Ch-Ua-Wow64": "?0",
    "Sec-Fetch-Dest": "document",
    "Sec-Fetch-Mode": "navigate",
    "Sec-Fetch-Site": "none",
    "Sec-Fetch-User": "?1",
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/114.0.0.0 Safari/537.36",
    "Cookie": "CONSENT=YES",
    "Referer": "https://www.google.com/",
}

SEP = "; "
ALLOWED_START = ["1P_JAR", "NID", "AEC", "DV", "OTZ"]


def cookie_handler(cookie: str) -> str:
    cookies_list = re.split(r"[, ;]", cookie)

    buf = StringIO()

    for cookie in cookies_list:
        for start in ALLOWED_START:
            if cookie.startswith(start):
                buf.write(cookie)
                buf.write(SEP)
                break

    return buf.getvalue()[:-2]
