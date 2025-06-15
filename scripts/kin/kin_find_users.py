import os
from bs4 import BeautifulSoup
import re
from argparse import ArgumentParser

from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager

from util.logger import setup_logger
from util.connection import get_html
from kin.header import kinheader
from util.env import AVAILABLE_IPS


user_pttn = re.compile(r"u=(.*)")
PROFESSIONALS = [
    "DOCTOR",
    "LAWYER",
    "LABOR",
    "ANIMALDOCTOR",
    "PHARMACIST",
    "TAXACC",
    "DIETITIAN",
    "CUSTOMSBROKER",
]

DEFAULT_IP = AVAILABLE_IPS[0]  # Default to the first available IP
IP = "192.168.0.1"  # Or, use your own IP address
# Set your ChromeDriver path here
DEFAULT_CHROME_DRIVER_PATH = "/path/to/chromedriver"
CHROME_DRIVER_PATH = DEFAULT_CHROME_DRIVER_PATH


def find_user(href):
    result = user_pttn.search(href)
    return result.group(1)


def professional_page_routine(profession, page, logger):
    url = f"https://kin.naver.com/people/expert/index.naver?orgId=0&sort=answerCount&edirId=0&type={profession}&page={page}"
    _, html = get_html(url, kinheader, logger=logger, ip=IP)
    soup = BeautifulSoup(html, "html.parser")

    selector = "#content > div.pro_listbox > ul > li > dl > dd > h5 > a"
    users = set(find_user(tag["href"]) for tag in soup.select(selector))

    selector = "#content > div.pro_listbox > ul > li > dl > dd > table > tr > td > em"
    last_tag = soup.select(selector)[-1]
    if last_tag is None:
        return users, False

    last_tag_text = last_tag.text
    if last_tag_text == "0":
        return users, False

    return users, len(users) == 10


def partner_page_routine(dirId, page, logger):
    url = f"https://kin.naver.com/people/partner/index.naver?dirId={dirId}&page={page}"
    _, html = get_html(url, kinheader, logger=logger, ip=IP)
    soup = BeautifulSoup(html, "html.parser")
    selector = "#content > ul > li > div.kinpartner_list__content > a.spot_partner__name.ellipsis"
    users = set(find_user(tag["href"]) for tag in soup.select(selector))

    # check if there is a next page
    selector = "#content > div.paginate._default_pager > a"
    tags = soup.select(selector)
    page_numbers = [int(tag.text) for tag in tags]
    logger.info(f"DirId: {dirId}, Last page: {page_numbers[-1]}")
    return users, page_numbers[-1] > page


def partner_routine(dirId, logger):
    page = 1
    remaining = True
    users = set()
    while remaining:
        new_users, remaining = partner_page_routine(dirId, page, logger)
        logger.info(f"DirId: {dirId}, Page: {page}, Users: {len(new_users)}")
        users.update(new_users)
        page += 1
    return users


def ranking_page_routine(page, logger):
    url = f"https://kin.naver.com/people/rank/index.naver?page={page}"

    # Selenium Chrome options
    chrome_options = Options()
    chrome_options.add_argument("--headless")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")

    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(
        service=service, options=chrome_options
    )
    driver.get(url)
    driver.implicitly_wait(5)
    selector = "#app > table > tbody > tr > td > a.nickname--3hDTP"
    tags = driver.find_elements(By.CSS_SELECTOR, selector)
    users = []
    for tag in tags:
        href = tag.get_attribute("href")
        if href is not None:
            users.append(find_user(href))
    users = set(users)
    return users


def ranking_routine(logger):
    users = set()
    for i in range(1, 51):
        new_users = ranking_page_routine(i, logger)
        logger.info(f"Ranking Page: {i}, Users: {len(new_users)}")
        users.update(new_users)
    return users


def professional_routine(profession, logger):
    page = 1
    remaining = True
    users = set()
    while remaining:
        new_users, remaining = professional_page_routine(
            profession, page, logger)
        logger.info(
            f"Profession: {profession}, Page: {page}, Users: {len(new_users)}")
        users.update(new_users)
        page += 1
    return users


def elite_routine(year, logger):
    url = f"https://kin.naver.com/people/elite/list.naver?year={year}"
    _, html = get_html(url, kinheader, logger=logger, ip=IP)
    soup = BeautifulSoup(html, "html.parser")
    selector = "#content > div > ol > li > div > a"
    tags = soup.select(selector)
    users = set(find_user(tag["href"]) for tag in tags)
    return users


result_path = "scripts/kin/kin_users.txt"


def main():
    parser = ArgumentParser(description="Find users from Naver Knowledge In")
    parser.add_argument("--ip", type=str, default=DEFAULT_IP,
                        help="IP address to use for requests")
    args = parser.parse_args()

    global IP
    IP = args.ip
    print(f"Using IP: {IP}")

    logger = setup_logger("find_users")
    if os.path.exists(result_path):
        with open(result_path) as f:
            user_set = set(f.read().splitlines())
    else:
        user_set = set()

    with open(result_path, "w") as f:
        # Write existing users to the file
        for user in user_set:
            f.write(user + "\n")

        # Collect users from elite section
        for year in range(2015, 2023):
            users = elite_routine(year, logger)
            new_users = users - user_set
            logger.info(f"Year: {year}, New users: {len(new_users)}")
            for user in new_users:
                f.write(user + "\n")
            user_set.update(new_users)

        # Collect users from professional and partner sections
        for profession in PROFESSIONALS:
            users = professional_routine(profession, logger)
            new_users = users - user_set
            logger.info(
                f"Profession: {profession}, New users: {len(new_users)}")
            for user in new_users:
                f.write(user + "\n")
            user_set.update(new_users)

        for dirId in list(range(1, 14)) + [20]:
            users = partner_routine(dirId, logger)
            new_users = users - user_set
            logger.info(f"DirId: {dirId}, New users: {len(new_users)}")
            for user in new_users:
                f.write(user + "\n")
            user_set.update(new_users)

        # Collect users from ranking section
        users = ranking_routine(logger)
        new_users = users - user_set
        logger.info(f"Ranking, New users: {len(new_users)}")
        if not new_users:
            return
        for user in new_users:
            f.write(user + "\n")


if __name__ == "__main__":
    main()
