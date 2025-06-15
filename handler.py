from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, StaleElementReferenceException
import re
import time
chrome_options = Options()
chrome_options.add_argument("--headless")
chrome_options.add_argument("--no-sandbox")
chrome_options.add_argument("--disable-dev-shm-usage")

driver = webdriver.Chrome(
    service=Service(ChromeDriverManager().install()),
    options=chrome_options
)

DELAY = 1


def wait_for_page_load_complete(driver, timeout=3):
    def page_loaded(driver):
        return driver.execute_script("return document.readyState") == "complete"
    try:
        WebDriverWait(driver, timeout).until(page_loaded)
        return True
    except TimeoutException:
        return False


def find_and_click_element(driver, selector):
    element = driver.find_element(By.CSS_SELECTOR, selector)
    click_element(driver, element)


def click_element(driver, element):
    try:
        driver.execute_script(
            "arguments[0].scrollIntoView({block: 'center'});", element)
        time.sleep(DELAY)
        element.click()
    except StaleElementReferenceException:
        element = driver.find_element(By.CSS_SELECTOR, element.selector)
    except Exception as e:
        return


url = "https://section.cafe.naver.com/ca-fe/home/rankings"
driver.get(url)
wait_for_page_load_complete(driver)
time.sleep(2 * DELAY)
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

task = (9, 10)
start = (len(category_dict) * task[0] // task[1])
end = (len(category_dict) * (task[0] + 1) // task[1])
max_page = 13


def handle_page(driver):
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
        cafe_id = re.search(r'naver.com/(.+)', new_url).group(1)
        new_cafes.append((cafe_name, cafe_id, cafe_member))
    return new_cafes


for catetory_idx in range(start, end):
    if catetory_idx == 0:
        continue
    category = category_dict[catetory_idx]
    # if not category is clickable:
    while not category.is_displayed() or not category.is_enabled():
        click_element(driver, next_button)
        time.sleep(DELAY)
    sub_theme_selector = "#mainContainer > div.cafe_type.themes.content > div > div:nth-child(1) > div > div.common_open_box > div > ul > li"

    click_element(driver, category)
    time.sleep(DELAY)
    sub_themes = driver.find_elements(By.CSS_SELECTOR, sub_theme_selector)
    if len(sub_themes) > 1:
        sub_themes = sub_themes[1:]
    print([sub_theme.text.strip() for sub_theme in sub_themes])
    new_cafes = []
    for sub_theme in sub_themes:
        page = 1
        driver.execute_script(
            "arguments[0].scrollIntoView({block: 'center'});", sub_theme)
        click_element(driver, sub_theme)
        wait_for_page_load_complete(driver)
        time.sleep(DELAY)
        total_button_selector = "#mainContainer > div.cafe_type.themes.content > div > div:nth-child(1) > div > div.type_list_wrap > ul > li:nth-child(3) > button"
        wait.until(EC.presence_of_element_located(
            (By.CSS_SELECTOR, total_button_selector)))
        total_button = driver.find_element(
            By.CSS_SELECTOR, total_button_selector)
        click_element(driver, total_button)
        time.sleep(DELAY)
        while page <= max_page:
            print(f"Processing page {page} of category {catetory_idx}")
            selector_idx = (page - 1) % 10 + 2
            page_selector = f"#mainContainer > div.cafe_type.themes.content > div > div.ArticlePaginate > button:nth-child({selector_idx})"
            print(f"Clicking page button: {page_selector}")
            wait.until(EC.presence_of_element_located(
                (By.CSS_SELECTOR, page_selector)))
            find_and_click_element(driver, page_selector)
            time.sleep(2 * DELAY)
            try:
                cafes = handle_page(driver)
                if not cafes:
                    break
                new_cafes.extend(cafes)
            except Exception as e:
                print(f"Error on page {page} of category {catetory_idx}: {e}")
                break
            if page % 10 == 0:
                next_page_selector = f"#mainContainer > div.cafe_type.themes.content > div > div.ArticlePaginate > button.btn.type_next"
                find_and_click_element(driver, next_page_selector)
                wait_for_page_load_complete(driver)
                time.sleep(DELAY)
            page += 1
            for cafe in new_cafes:
                print(
                    f"Cafe Name: {cafe[0]}, Cafe ID: {cafe[1]}, Members: {cafe[2]}")
