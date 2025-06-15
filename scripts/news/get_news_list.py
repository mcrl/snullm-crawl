import requests
from bs4 import BeautifulSoup

url = "https://news.naver.com/main/officeList.naver"
selector = "#groupOfficeList > table > tbody > tr > td > ul > li > a"

response = requests.get(url)
soup = BeautifulSoup(response.content, 'html.parser')
tags = soup.select(selector)

with open('navernews_available.txt', 'w') as file:
    for tag in tags:
        txt = tag.text.strip()
        if "언론사 최신기사" in txt:
            continue
        file.write(txt + '\n')

url = "https://news.daum.net/cplist"
selector = "#dcc1cfb8-ad2a-4d8b-ba39-32bbd69cde8b > div.baseinfo_list > dl > dd > div > a"

response = requests.get(url)
soup = BeautifulSoup(response.content, 'html.parser')
tags = soup.select(selector)

with open('daumnews_available.txt', 'w') as file:
    for tag in tags:
        txt = tag.text.strip()
        if "언론사 최신기사" in txt:
            continue
        file.write(txt + '\n')
