import os
import json
import re
import http.client

import time
from datetime import datetime, timedelta

# Replace the import from __utils with imports from util modules
from util.logger import setup_logger
from util.connection import get_html, make_https_connection
from util.fileutil import read_txt
from util.utils import get_retrieval_date
from .__utils import update_bloginfo, load_html, scrap_html

class NaverBlogScrapper():
    def __init__(self, ip, config):
        self.bloglist_path = config["bloglist_path"]
        self.postlist_path = config["postlist_path"]
        self.html_path = config["html_path"]
        self.jsonl_path = config["jsonl_path"]

        self.ip = ip
        self.logger = setup_logger(ip)
    
    def send_postlist_apicall(self, blogid, page):
        path = f"/PostTitleListAsync.naver?blogId={blogid}&viewdate=&currentPage={page}&categoryNo=0&parentCategoryNo=&countPerPage=30"
        save_path = os.path.join(self.html_path, f"{blogid}/postlist_{page}.html")
        if os.path.exists(save_path):
            return load_html(save_path)

        conn = http.client.HTTPSConnection("blog.naver.com", 443, source_address=(self.ip, 0))

        soup, self.headers = scrap_html(conn, path, self.headers, save_path, self.logger)
        conn.close()
        return soup
    
    def get_post_html(self, blogid, postid):
        path = f"/PostView.naver?blogId={blogid}&logNo={postid}"
        save_path = os.path.join(self.html_path, f"{blogid}/{postid}.html")
        if os.path.exists(save_path):
            return load_html(save_path)

        conn = http.client.HTTPSConnection("m.blog.naver.com", 443, source_address=(self.ip, 0))
        soup, self.headers = scrap_html(conn, path, self.headers, save_path, self.logger)
        conn.close()
        return soup

    def handle_api_call(self, soup, retry_cnt, blogid, page, lock):
        if retry_cnt >= 10:
            raise Exception(f"{self.ip} Blocked")
        if soup == -999 or "게시물이 삭제되었거나 다른 페이지로 변경되었습니다" in soup.text:
            self.logger.warning(f"Error occured during get postlist of {blogid}, {page}th page")
            return [], 0

        try:
            parsed = json.loads(soup.text)
        except Exception as e:
            self.logger.warning(f"Error occured while loading postlist api resp. {blogid}, {page}th page: {e}")
            return [], 0
        
        if parsed["resultCode"] == "E":
            self.logger.warning(f"{blogid} Empty")
            update_bloginfo(None, blogid)
            return [], 0
        
        return parsed["tagQueryString"].split("&logNo=")[1:], int(parsed["totalCount"]) // 30
        
    def handle_http_call(self, soup, retry_cnt, block_cnt, postid):
        overlays = []

        if retry_cnt == 10:
            raise Exception(f"{self.ip} Blocked")
        if soup == -999:
            self.logger.warning(f"Error occurred while parsing post {postid}")
            block_cnt += 1
            return overlays, block_cnt
        
        if soup.select_one(".se-module.se-module-text.se-title-text"):
            overlays = [".se-module.se-module-text.se-title-text", ".se-component.se-text.se-l-default"]    
        elif soup.select_one(".tit_area"):
            overlays = [".tit_area", ".post_ct"]
        elif soup.select_one(".se_editArea"):
            overlays = [".se_editArea", ".se_component.se_paragraph"]
        else:
            self.logger.warning(f"{postid}, Unexpected structure")
        
        return overlays, block_cnt

    def get_postlist(self, blogid, lock):
        save_path = os.path.join(self.postlist_path, f"{blogid}.txt")
        if os.path.exists(save_path):
            try:
                with open(save_path, 'r') as f:
                    postlist = json.load(f)
                return postlist
            except:
                pass
        
        self.headers = {
            "Accept": "*/*",
            "Accept-Encoding": "gzip, deflate, br",
            "Accept-Language": "ko,en-US;q=0.9,en;q=0.8,ja;q=0.7",
            "Charset": "utf-8",
            "Connection": "keep-alive",
            "Content-Type": "application/x-www-form-urlencoded; charset=utf-8",
            "Cookie": "",
            "Host": "blog.naver.com",
            "Referer": f"https://blog.naver.com/PostList.naver?blogId={blogid}&widgetTypeCall=true&directAccess=true",
            "Sec-Ch-Ua": '"Not.A/Brand";v="8", "Chromium";v="114", "Google Chrome";v="114"',
            "Sec-Ch-Ua-Mobile": "?0",
            "Sec-Ch-Ua-Platform": "Windows",
            "Sec-Fetch-Dest": "empty",
            "Sec-Fetch-Mode": "cors",
            "Sec-Fetch-Site": "same-origin",
            "user-agent" : "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/114.0.0.0 Safari/537.36"
        }

        soup = -998
        retry_cnt = 0

        while soup == -998 and retry_cnt < 10:
            soup = self.send_postlist_apicall(blogid, 1)
            retry_cnt += 1
        
        postlist, totalpage = self.handle_api_call(soup, retry_cnt, blogid, 1, lock)

        if not postlist:
            return postlist

        for i in range(totalpage):
            time.sleep(1)

            soup = -998
            retry_cnt = 0
            while soup == -998 and retry_cnt < 10:
                soup = self.send_postlist_apicall(blogid, i + 2)
                retry_cnt += 1
            
            temp, _ = self.handle_api_call(soup, retry_cnt, blogid, i + 2, lock)
            postlist += temp
        
        with open(save_path, 'w') as f:
            json.dump(postlist, f)
        
        return postlist

    def parse_post(self, soup, overlays, uri):
        js = {"uri": uri}
        try:
            contents = soup.select_one(overlays[0])
            js["title"] = re.sub(r'(\n)+', '\n', contents.text.replace('\u200b', ''))[1:-1].strip()

            contents = soup.select_one(".blog_date, .se_date")
            js["created_date"] = re.sub(r"[\n\t\u200b]", "", contents.text).strip()

            current_time = datetime.now()
            js["retrieval_date"] = current_time.strftime("%Y-%m-%dT%H:%M:%SZ")

            if "시간" in js["created_date"]:
                hours = int(js["created_date"][:-4])
                created_time = current_time - timedelta(hours=hours)
            elif "분" in js["created_date"]:
                minutes = int(js["created_date"][:-3])
                created_time = current_time - timedelta(minutes=minutes)
            elif "초" in js["created_date"]:
                seconds = int(js["created_date"][:-3])
                created_time = current_time - timedelta(seconds = seconds)
            else:
                created_time = datetime.strptime(js["created_date"], "%Y. %m. %d. %H:%M")
            
            js["created_date"] = created_time.strftime("%Y-%m-%d")

            hashtag = soup.select_one(".post_tag")
            if hashtag:
                js["hashtag"] = soup.select_one(".post_tag").text[2:-2]
            else:
                js["hashtag"] = ""
            
            try:
                js["comment_num"] = re.search(r'\d+', soup.select_one(".btn_r").text).group()
            except:
                js["comment_num"] = ""
            
            js["type"] = "naver_blog"
            js["lang"] = "kor"

            contents = soup.select(overlays[1])
            js["text"] = ""
            for i in range(len(contents)):
                js["text"] += contents[i].text
            
            js["text"] = re.sub(r'(\n)+', '\n', js["text"].replace('\u200b', ''))[1:]

            if js["text"] == "":
                self.logger.warning(f"{uri}, Post empty")
                return {}

            for key in js.keys():
                js[key] = re.sub(r'[\ud800-\udbff\udc00-\udfff]', '', js[key])

        except Exception as e:
            self.logger.warning(f"Error occured while parsing {uri}, {e} occured")
            return {}
        
        return js

    def scrap_naverblog(self, blogid, lock):
        start = time.time()
        self.logger.info(f"Scrapping {blogid}")

        self.logger.info("Getting postlist")
        postlist = self.get_postlist(blogid, lock)
        if len(postlist) == 0:
            return []
        
        jsonl = []
        self.logger.info("Scrapping posts")

        if not os.path.exists(os.path.join(self.html_path, f"{blogid}")):
            os.makedirs(os.path.join(self.html_path, f"{blogid}"))

        self.headers = {
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7",
            "Accept-Encoding": "gzip, deflate, br",
            "Accept-Language": "ko,en-US;q=0.9,en;q=0.8,ja;q=0.7",
            "Cookie": "",
            "Referer": f"https://m.blog.naver.com/{blogid}/",
            "Sec-Ch-Ua": '"Not.A/Brand";v="8", "Chromium";v="114", "Google Chrome";v="114"',
            "Sec-Ch-Ua-Mobile": "?0",
            "Sec-Ch-Ua-Platform": "Windows",
            "Sec-Fetch-Dest": "document",
            "Sec-Fetch-Mode": "navigate",
            "Sec-Fetch-Site": "same-origin",
            "Sec-Fetch-User": "?1",
            "Upgrade-Insecure-Requests": "1",
            "user-agent" : "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/114.0.0.0 Safari/537.36"
        }

        cnt = 0
        block_cnt = 0
        empty_post_cnt = 0

        for postid in postlist:
            if block_cnt > 10:
                raise Exception(f"{self.ip} Blocked")
            if cnt % 100 == 99:
                self.logger.info(f"Progressing... {cnt + 1} / {len(postlist)}")
            if cnt == 500:
                if empty_post_cnt / cnt > 0.8:
                    self.logger.warning(f"Skip {blogid}")
                    update_bloginfo(None, blogid)
                    return []
            time.sleep(1)
            cnt += 1

            uri = f"m.blog.naver.com/{blogid}/{postid}"

            soup = -998
            retry_cnt = 0

            while soup == -998 and retry_cnt < 10:
                soup = self.get_post_html(blogid, postid)
                retry_cnt += 1
            
            overlays, block_cnt = self.handle_http_call(soup, retry_cnt, block_cnt, postid)
            if not overlays:
                continue
            
            self.headers["Referer"] = f"https://{uri}"

            js = self.parse_post(soup, overlays, uri)
            if not js:
                empty_post_cnt += 1
            else:
                jsonl.append(js)
            block_cnt = 0
        
        if not jsonl:
            self.logger.warning(f"{blogid} empty")
            update_bloginfo(None, blogid)
            return []

        self.logger.info(f"Scrapped {blogid}, took {time.time()-start:.2f} seconds")

        return jsonl
