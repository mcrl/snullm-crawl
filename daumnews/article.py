import json
from util.utils import get_retrieval_date


def dump_article(text, uri, crawl_method, office, created_date, article_title):
    payload = {}
    payload["text"] = text
    payload["retrieval_date"] = get_retrieval_date()
    payload["uri"] = uri
    payload["type"] = crawl_method
    payload["article_source"] = office
    payload["created_date"] = created_date
    payload["article_title"] = article_title
    return json.dumps(payload, ensure_ascii=False)
