from logging import Logger
from typing import Dict, Any, List, Tuple, Optional
import datetime
from bs4 import BeautifulSoup
import json
from io import StringIO
import os.path as osp
import multiprocessing as mp
import re
import time

from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, StaleElementReferenceException

from util.misc import get_interval
from util.customexception import *
from util.ema import Ema
from cafelist.cache import read_cache, write_cache


def handle_cafe_id(
    task: Tuple[int, int],
    shared_argv: Dict[str, Any],
    private_argv: Dict[str, Any],
    logger: Logger,
    save_queue: Optional[mp.Queue] = None,
):
    # setup variables
    ip = private_argv["ip"]
    interval = get_interval(shared_argv, private_argv)

    max_page = shared_argv.get("max_page", 10)
    print(f"Using max_page: {max_page} for task {task}")

    # setup Chrome driver
    chrome_options = Options()
    chrome_options.add_argument("--headless")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--allowed-ips=" + ip)

    driver = webdriver.Chrome(
        service=Service(ChromeDriverManager().install()),
        options=chrome_options
    )

    cafe_list_url = "https://section.cafe.naver.com/ca-fe/home/rankings"
    driver.get(cafe_list_url)
    wait_for_page_load_complete(driver)
    time.sleep(2 * interval)
    wait = WebDriverWait(driver, 10)
    theme_selector = "#mainContainer > div.cafe_type.themes.content > div > div:nth-child(1) > div.cafe_type_tab > div.common_scroll_box > div > ul > li"
    wait.until(EC.presence_of_all_elements_located(
        (By.CSS_SELECTOR, theme_selector)))
    categories = driver.find_elements(By.CSS_SELECTOR, theme_selector)
    category_dict = {}
    for idx, category in enumerate(categories):
        if category.text.strip():
            category_dict[idx] = category
    button_selector = "#mainContainer > div.cafe_type.themes.content > div > div:nth-child(1) > div > div.common_scroll_box > button.btn.btn_scroll_next"

    next_button = driver.find_element(By.CSS_SELECTOR, button_selector)

    for i in range(len(category_dict) - 1):
        category_dict[i] = category_dict[i+1]
    del category_dict[len(category_dict) - 1]
    # task (index, total)
    start = (len(category_dict) * task[0] // task[1])
    end = (len(category_dict) * (task[0] + 1) // task[1])
    logger.info(f"Processing categories from {start} to {end}")

    for category_idx in range(start, end):
        category = category_dict[category_idx]
        while not category.is_displayed() or not category.is_enabled():
            click_element(driver, next_button)
            time.sleep(interval)
        sub_theme_selector = "#mainContainer > div.cafe_type.themes.content > div > div:nth-child(1) > div > div.common_open_box > div > ul > li"

        click_element(driver, category)
        time.sleep(interval)
        sub_themes = driver.find_elements(By.CSS_SELECTOR, sub_theme_selector)
        if len(sub_themes) > 1:
            sub_themes = sub_themes[1:]
        logger.info([sub_theme.text.strip() for sub_theme in sub_themes])
        for sub_theme in sub_themes:
            sub_theme_name = sub_theme.text.strip()
            cache_path = f"{category_idx}_{sub_theme_name.replace('/', '_')}"
            cached_page = read_cache(cache_path)
            page = cached_page + 1
            move_to_page(driver, page, interval)
            driver.execute_script(
                "arguments[0].scrollIntoView({block: 'center'});", sub_theme)
            click_element(driver, sub_theme)
            wait_for_page_load_complete(driver)
            time.sleep(interval)
            total_button_selector = "#mainContainer > div.cafe_type.themes.content > div > div:nth-child(1) > div > div.type_list_wrap > ul > li:nth-child(3) > button"
            wait.until(EC.presence_of_element_located(
                (By.CSS_SELECTOR, total_button_selector)))
            total_button = driver.find_element(
                By.CSS_SELECTOR, total_button_selector)
            click_element(driver, total_button)
            time.sleep(interval)
            while page <= max_page:
                logger.info(
                    f"Processing sub-theme: {sub_theme_name} on page {page}")
                selector_idx = (page - 1) % 10 + 2
                page_selector = f"#mainContainer > div.cafe_type.themes.content > div > div.ArticlePaginate > button:nth-child({selector_idx})"
                wait.until(EC.presence_of_element_located(
                    (By.CSS_SELECTOR, page_selector)))
                find_and_click_element(driver, page_selector)
                time.sleep(2 * interval)
                try:
                    cafes = handle_page(driver, logger)
                    if not cafes:
                        break
                    for cafe in cafes:
                        cafe_obj = {
                            "cafe_name": cafe[0],
                            "cafe_id": cafe[1],
                            "cafe_member": cafe[2],
                        }
                        save_queue.put(json.dumps(
                            cafe_obj, ensure_ascii=False))
                except Exception as e:
                    print(
                        f"Error on page {page} of category {category_idx}: {e}")
                    break
                if page % 10 == 0:
                    next_page_selector = f"#mainContainer > div.cafe_type.themes.content > div > div.ArticlePaginate > button.btn.type_next"
                    find_and_click_element(driver, next_page_selector)
                    wait_for_page_load_complete(driver)
                    time.sleep(interval)
                write_cache(cache_path, str(page))
                page += 1


def move_to_page(driver, page_number: int, interval: int = 1):
    page = 1
    if page_number - page > 10:
        page_number = page + 10
        next_page_selector = f"#mainContainer > div.cafe_type.themes.content > div > div.ArticlePaginate > button.btn.type_next"
        find_and_click_element(driver, next_page_selector)
        wait_for_page_load_complete(driver)
        time.sleep(interval)
    selector_idx = (page - 1) % 10 + 2
    page_selector = f"#mainContainer > div.cafe_type.themes.content > div > div.ArticlePaginate > button:nth-child({selector_idx})"
    find_and_click_element(driver, page_selector)
    wait_for_page_load_complete(driver)
    time.sleep(interval)


def handle_page(driver, logger):
    wait = WebDriverWait(driver, 10)
    cafe_selector = "#mainContainer > div.cafe_type.themes.content > div > div.home_theme_frame > div"
    wait.until(EC.presence_of_all_elements_located(
        (By.CSS_SELECTOR, cafe_selector)))
    cafes = driver.find_elements(By.CSS_SELECTOR, cafe_selector)
    new_cafes = []
    for cafe in cafes:
        wait.until(EC.presence_of_element_located(
            (By.CSS_SELECTOR, "strong.cafe_name")))
        cafe_name = cafe.find_element(By.CSS_SELECTOR, "strong.cafe_name")
        if cafe_name:
            cafe_name = cafe_name.text.strip()
        else:
            cafe_name = "Unknown Cafe"
        cafe_member_selector = "span.data.member"
        cafe_member = cafe.find_element(By.CSS_SELECTOR, cafe_member_selector)
        cafe_member = cafe_member.text.strip()
        driver.execute_script("arguments[0].target='_blank';", cafe)
        click_element(driver, cafe)
        driver.switch_to.window(driver.window_handles[-1])
        new_url = driver.current_url
        driver.close()
        driver.switch_to.window(driver.window_handles[0])
        if "login" in new_url:
            logger.warning(
                f"Login required for cafe: {cafe_name}, URL: {new_url}")
            continue
        cafe_id = re.search(r'naver.com/(.+)', new_url).group(1)
        new_cafes.append((cafe_name, cafe_id, cafe_member))
    return new_cafes


def wait_for_page_load_complete(driver, timeout=3):
    def page_loaded(driver):
        return driver.execute_script("return document.readyState") == "complete"
    try:
        WebDriverWait(driver, timeout).until(page_loaded)
        return True
    except TimeoutException:
        return False


def find_and_click_element(driver, selector, interval=1):
    element = driver.find_element(By.CSS_SELECTOR, selector)
    click_element(driver, element, interval=interval)


def click_element(driver, element, interval=1):
    try:
        driver.execute_script(
            "arguments[0].scrollIntoView({block: 'center'});", element)
        time.sleep(interval)
        element.click()
    except StaleElementReferenceException:
        element = driver.find_element(By.CSS_SELECTOR, element.selector)
    except Exception as e:
        return
