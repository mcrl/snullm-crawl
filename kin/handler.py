import os
from bs4 import BeautifulSoup
import re
import time

from util.connection import get_html
from util.misc import get_interval
from kin.header import kinheader
from kin.structs import KinBestDir, KinBestPage, Document, KinUser
from kin.parser import parse_html

from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager

dirId_pttn = re.compile(r"dirId=\d+")
docId_pttn = re.compile(r"docId=\d+")
NAVER_MAX_PAGE = 100


def days_passed(timestamp, days=30):
    return time.time() - timestamp > 60 * 60 * 24 * days


def get_max_pages(dirId, logger):
    url = f"https://kin.naver.com/best/listaha.naver?svc=KIN&dirId={dirId}"
    _, html = get_html(url, kinheader, logger=logger)

    soup = BeautifulSoup(html, "html.parser")

    # last button: a.next (last one)
    last_button = soup.select("a.next")
    if not last_button:
        selector = "#ahaList_2 > div.section_paginate > div.paginate._default_pager > a"
        last_child = soup.select(selector)[-1]
        if not last_child:
            logger.info("cannot get last page")
            last_page = 1
        else:
            last_page = int(last_child.text)
    else:
        # see link: it gives the last page number
        last_page = int(last_button[-1]["href"].split("=")[-1])
    return last_page


def _url_to_doc(url):
    try:
        dirId = int(re.search(dirId_pttn, url).group().split("=")[-1])
        docId = int(re.search(docId_pttn, url).group().split("=")[-1])
        return Document(dirId, docId)
    except:
        return None


def get_documents(dirId, page, logger):
    url = f"https://kin.naver.com/best/listaha.naver?svc=KIN&dirId={dirId}&page={page}"
    _, html = get_html(url, kinheader, logger=logger)
    soup = BeautifulSoup(html, "html.parser")
    selector = "#au_board_list > tr > td.title > a"
    tags = soup.select(selector)
    documents = [_url_to_doc(tag["href"]) for tag in tags]
    documents = [document for document in documents if document is not None]
    return documents


def best_dir_routine(dirId, logger):
    # https://kin.naver.com/best/listaha.naver?svc=KIN&dirId=9
    kin_dir = KinBestDir(dirId, 0)
    kin_dir.restore_from_cache()
    if kin_dir.done:
        return
    if kin_dir.max_pages == 0:
        kin_dir.max_pages = get_max_pages(dirId, logger)
        kin_dir.save_to_cache()
    for i in range(1, kin_dir.max_pages + 1):
        best_page = KinBestPage(dirId, i)
        best_page.restore_from_cache()
        if best_page.done:
            continue
        if len(best_page.documents) == 0:
            documents = get_documents(dirId, i, logger)
            best_page.documents = documents
            best_page.save_to_cache()
        for doc in best_page.documents:
            if not os.path.exists(doc.save_path):
                _, html = get_html(doc.url, kinheader, logger=logger)
                with open(doc.save_path, "w") as f:
                    f.write(html)
        best_page.done = True
        best_page.save_to_cache()
    kin_dir.done = True
    kin_dir.save_to_cache()


def find_user_docs_page(user, dirId, page, logger, year=None, ip=None, interval=1):
    url = f"https://kin.naver.com/userinfo/answerList.naver?dirId={dirId}&u={user.userId}&isWorry=false&page={page}"
    url += f"&year={year}" if year else ""
    _, html = get_html(url, kinheader, ip=ip, logger=logger, interval=interval)
    soup = BeautifulSoup(html, "html.parser")
    selector = "#au_board_list > tr > td.title > a"
    tags = soup.select(selector)
    documents = [_url_to_doc(tag["href"]) for tag in tags]
    logger.info(
        f"User: {user.userId}, dirId: {dirId}, page: {page}, len: {len(documents)}"
    )

    return documents


def process_docs(
    docs, logger, ip=None, interval=1, save_queue=None, ignore_error=False
):
    # we track if any document is saved. If no document is processed, we do not need to proceed certain directory.
    cnt = 0
    for doc in docs:
        if not os.path.exists(doc.save_path):
            _, html = get_html(
                doc.url, kinheader, logger=logger, ip=ip, interval=interval
            )
            if html is None:
                if ignore_error:
                    continue
                return
            with open(doc.save_path, "w") as f:
                f.write(html)
            parsed = parse_html(html, doc)
            if parsed is not None and save_queue is not None:
                save_queue.put(parsed.to_json())
            cnt += 1
    return cnt


def process_user_dir_docs(
    user, dirId, years, logger, ip=None, interval=1, save_queue=None
):
    # we first search the first page to see if there are too many documents
    docs = find_user_docs_page(
        user, dirId, 1, logger, year=None, ip=ip, interval=interval
    )
    if len(docs) < 20:
        years = [None]
        process_docs(
            docs,
            logger,
            ip=ip,
            interval=interval,
            save_queue=save_queue,
            ignore_error=True,
        )
        return docs

    user_docs = []
    curr_page = 1

    # There are more than 20 documents in this directory.
    # We need to check if we need to split the search by year
    # If 99th page is not the last page, we need to split the search by year
    docs = find_user_docs_page(user, dirId, 99, logger, year=None, ip=ip)

    # if we do not need to split search, we reuse first page
    if len(docs) < 20:
        years = [None]
        curr_page = 2
        user_docs = docs

    dir_done = False  # a flag to check if we need to stop searching this directory
    for year in years:
        if dir_done:
            break
        while curr_page < NAVER_MAX_PAGE:
            documents = find_user_docs_page(
                user, dirId, curr_page, logger, year=year, ip=ip
            )
            cnt = process_docs(
                documents,
                logger,
                ip=ip,
                interval=interval,
                save_queue=save_queue,
                ignore_error=True,
            )
            user_docs.extend(documents)
            stop = len(documents) < 20
            if stop:
                break
            if cnt == 0:
                dir_done = True  # we consider this directory is done
            curr_page += 1
        curr_page = 1
    return user_docs


def find_user_metainfo(user, logger, ip=None, interval=1):
    def _extract_dirid(param):
        pttn = r"\d+"
        match = re.search(pttn, param)
        return int(match.group()) if match else 0

    url = f"https://kin.naver.com/userinfo/answerList.naver?u={user.userId}"
    _, html = get_html(url, kinheader, logger=logger, interval=interval)
    soup = BeautifulSoup(html, "html.parser")

    # username
    selector = "#au_main_profile_box > div.my_personal_inner.my_personal_simple > div.profile_section._profile_section > div > div > a > strong"
    selector2 = "#container > div > div > div > div.my_personal_inner.my_personal_simple > div.profile_section > div > div > a > strong"
    selected = soup.select_one(selector)
    if selected is None:
        selected = soup.select_one(selector2)
    if selected is None:
        logger.error(f"cannot find user metainfo: {user}")
        return False
    user.username = selected.text

    # 크롬 옵션 설정 (옵션에 따라 브라우저 창을 표시하지 않을 수도 있음)
    chrome_options = Options()
    chrome_options.add_argument("--headless")  # 브라우저 창 없이 실행 (선택 사항)
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")

    service = Service(ChromeDriverManager().install())
    # service = Service(executable_path=chrome_driver_path)
    driver = webdriver.Chrome(
        service=service, options=chrome_options
    )

    # 대상 URL로 이동
    url = f"https://kin.naver.com/userinfo/answerList.naver?u={user.userId}"
    driver.get(url)

    selector = "#au_directory_sorting_dir > div > a"
    # click the button
    driver.find_element(By.CSS_SELECTOR, selector).click()
    driver.implicitly_wait(5)

    # get the list item
    selector = "#au_directory_sorting_dir > div > div > ul > li > a"
    tags = driver.find_elements(By.CSS_SELECTOR, selector)
    # show class names of tags
    dirIds = [_extract_dirid(tag.get_attribute("class")) for tag in tags]
    dirIds = [dirId for dirId in dirIds if dirId != 0]

    # click the button
    selector = "#au_year_sorting > div > a"
    driver.find_element(By.CSS_SELECTOR, selector).click()
    driver.implicitly_wait(5)
    selector = "#au_year_sorting > div > div > ul > li > a"
    tags = driver.find_elements(By.CSS_SELECTOR, selector)
    years = [tag.text for tag in tags if tag]
    years = [int(year) for year in years if year.isdigit()]

    user.dirIds = {dirId: False for dirId in dirIds}
    user.years = years
    user.metainfo_ready = True
    user.save_to_cache()
    return True


def handle_user_routine(user, logger, ip=None, interval=1, save_queue=None):
    user.restore_from_cache()
    # if user is ready and the cache timestamp has not passed more than 1 month, we skip
    if user.ready and not days_passed(user.cache_timestamp):
        return
    if not user.metainfo_ready:
        if not find_user_metainfo(user, logger, ip=ip, interval=interval):
            return

    if not user.user_docs:
        user.user_docs = []
    user_docs = user.user_docs
    for dirId in user.dirIds:
        if user.dirIds[dirId]:
            continue
        user_docs.extend(
            process_user_dir_docs(
                user,
                dirId,
                user.years,
                logger,
                ip=ip,
                interval=interval,
                save_queue=save_queue,
            )
        )
        user.user_docs = user_docs
        user.dirIds[dirId] = True
        user.save_to_cache()
    user.ready = True
    user.save_to_cache()


def handle_user(
    user: KinUser,
    shared_argv: dict,
    private_argv: dict,
    logger,
    save_queue=None,
):
    logger.warning("Handling user %s", user)
    ip = private_argv["ip"]
    interval = get_interval(shared_argv, private_argv)
    save_queue = save_queue
    handle_user_routine(user, logger, ip=ip,
                        interval=interval, save_queue=save_queue)
