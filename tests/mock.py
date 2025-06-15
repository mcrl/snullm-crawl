import requests


class MockResponse:
    def fetch_html(self, uri, logger, ip):
        html = requests.get(uri).text
        return html


class MockCache:

    def read_cached_html(uri):
        return None

    def naver_read_cached_html(oid, aid):
        return None

    def daum_save_html(uri, html):
        pass

    def naver_save_html(oid, html):
        pass
