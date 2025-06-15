import logging
import re
import subprocess
import pandas as pd

import time

import json
import gzip

import os
import sys

import http.client
from bs4 import BeautifulSoup

pd.options.mode.chained_assignment = None

def load_html(save_path):      
    with open(save_path, "r", encoding="utf-8") as f:
        html = f.read()
    soup = BeautifulSoup(html, 'html.parser')
    return soup

def scrap_html(conn, path, headers, save_path, logger):
    filename = save_path.split("/")[-1]
    if not os.path.exists(save_path[:-len(filename)]):
        os.makedirs(save_path[:-len(filename)])

    try:
        conn.request('GET', path, headers=headers)

        resp = conn.getresponse()
        cookie = resp.getheader("Set-Cookie")
        if cookie:
            headers["Cookie"] = cookie[:cookie.find(";")]
        encoding = resp.getheader("Content-Encoding")

        if encoding == "gzip":
            data = gzip.decompress(resp.read())
        else:
            data = resp.read()

        soup = BeautifulSoup(data, 'html.parser')

        if os.path.isdir(save_path):
            os.rmdir(save_path)

        with open(save_path, 'w', encoding="utf-8") as f:
            html = re.sub(r'[\ud800-\udbff\udc00-\udfff]', '', soup.prettify())
            clean_html = html.encode('utf-8', 'replace').decode('utf-8')
            f.write(clean_html)

    except http.client.RemoteDisconnected as e:
        logger.warning(f"Closed connection: {e}")
        return -998, headers

    except Exception as e:
        logger.warning(f"Error occurred while scrapping and saving html: {e}")
        return -999, headers

    return soup, headers

def load_bloginfos():
    try:
        blog_info = pd.read_csv("cache/naverblog/blog_info.csv", index_col=0)
    except:
        blog_info = pd.DataFrame(columns = ["blogid", "save_path", "checkpoint"])
        blog_info.to_csv("cache/naverblog/blog_info.csv")

    return blog_info

def update_bloginfo(js, save_path):
    blog_info = pd.read_csv("cache/naverblog/blog_info.csv", index_col=0)

    if js:
        uri = js["uri"]
        _, blogid, postid = uri.split("/")
    
        new_data = {"blogid": [blogid], "save_path": [save_path], "checkpoint": [postid]}
    else:
        new_data = {"blogid": [save_path], "save_path": [-1], "checkpoint": [-1]}
        
    blog_info = pd.concat([blog_info, pd.DataFrame(new_data)], ignore_index=True)
    blog_info.to_csv("cache/naverblog/blog_info.csv")

