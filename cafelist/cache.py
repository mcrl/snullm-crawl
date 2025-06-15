import os


def read_cache(task):
    cache_path = os.path.join('cache', 'navercafe_id', f"{task}.txt")
    if not os.path.exists(cache_path):
        return 0
    with open(cache_path, "r", encoding="utf-8") as f:
        page = f.read()
    try:
        page = int(page)
    except ValueError:
        return 0
    return page


def write_cache(task, page):
    cache_path = os.path.join('cache', 'navercafe_id', f"{task}.txt")
    if not os.path.exists(os.path.dirname(cache_path)):
        os.makedirs(os.path.dirname(cache_path))
    with open(cache_path, "w", encoding="utf-8") as f:
        f.write(page)
