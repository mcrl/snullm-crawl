from model.crawler import Crawler
import yaml
import json
import time
import socket
from logging import Logger
from typing import Dict, Any, List
import os
import traceback
import pandas as pd

from .NaverBlogScrapper import NaverBlogScrapper
from .__utils import load_bloginfos
from util.env import get_iplist
from util.argcheck import parse_iplist
from util.slack import send_slack_message


class naverblogCrawler(Crawler):
    def __init__(self, **kwargs):
        super(naverblogCrawler, self).__init__()
        self.save_id = "naverblog"
        self.save_dir = "data/naverblog/jsonl"
        self.cache_dir = "cache/naverblog"

    def load_configuration(self, config_file: str):
        with open(config_file, "r") as file:
            data_dict = yaml.safe_load(file)

        ips = data_dict.get("ips")
        default_interval = data_dict.get("default_interval", 1)
        if ips is not None:
            ips, intervals = parse_iplist(ips, default_interval=default_interval)
        if ips is None or len(ips) == 0:
            ips = get_iplist()
            intervals = [default_interval] * len(ips)

        private_args = []
        for ip, interval in zip(ips, intervals):
            argv = {"ip": ip, "interval": interval}
            private_args.append(argv)

        shared_argv = {}
        tasks = []

        bloglist_path = data_dict.get("bloglist_path", "cache/naverblog/bloglist.json")
        postlist_path = data_dict.get("postlist_path", "cache/naverblog/postlist/")
        html_path = data_dict.get("html_path", "data/naverblog/html/")
        jsonl_path = data_dict.get("jsonl_path", "data/naverblog/jsonl/")

        os.makedirs(postlist_path, exist_ok=True)
        os.makedirs(html_path, exist_ok=True)
        os.makedirs(jsonl_path, exist_ok=True)
        
        with open(bloglist_path, 'r') as f:
            blogids = json.loads(f.read())
        
        # Build task list
        blog_info = load_bloginfos()
        completed_blog = set(list(blog_info["blogid"]))
        
        # Filter out completed blogs
        tasks = [blogid for blogid in blogids if blogid not in completed_blog]
        
        shared_argv.update({
            "configuration": data_dict
        })
        
        return tasks, shared_argv, private_args

    def load_save_configuration(self, config_file: str):
        with open(config_file, "r") as file:
            data_dict = yaml.safe_load(file)
        save_id = data_dict.get("save_id", self.save_id)
        save_dir = data_dict.get("save_dir", self.save_dir)
        return save_id, save_dir
        
    def worker_routine(self, payload, shared_argv, private_argv, logger, save_queue=None):
        try:
            blogid = payload
            ip = private_argv["ip"]
            interval = private_argv.get("interval", 1)
            configuration = shared_argv["configuration"]
            
            logger.info(f"Start processing blog ID: {blogid}")
            scrapper = NaverBlogScrapper(ip, configuration)
            results = scrapper.scrap_naverblog(blogid, None)  # No lock needed with engine
            
            time.sleep(interval)
            
            # Pass results to the engine's save queue for the saver process to handle
            if save_queue is not None and results:
                # Update blog_info.csv to mark this blog as completed
                try:
                    # Get the first post's ID to use as checkpoint
                    first_result = results[0]
                    uri = first_result["uri"]
                    _, _, postid = uri.split("/")
                    
                    # Update blog info with the save path and post ID
                    save_path = os.path.join(self.save_dir, f"{self.save_id}_00000.jsonl")
                    self._update_blog_info(blogid, save_path, postid)
                    
                    logger.info(f"Updated blog_info.csv for blog ID: {blogid}")
                except Exception as e:
                    logger.error(f"Failed to update blog_info.csv: {str(e)}")
                
                # Send results to save queue
                for result in results:
                    # The saver_wrapper in engine.py expects JSON strings
                    json_str = json.dumps(result, ensure_ascii=False)
                    save_queue.put(json_str)
                
            logger.info(f"Finished processing blog ID: {blogid}")
            return results
            
        except Exception as e:
            error_msg = f"Exception occurred while scrapping naver blog: {str(e)}"
            logger.error(error_msg)
            logger.error(traceback.format_exc())
            
            if "Blocked" in str(e):
                logger.warning(f"Possible IP block while scrapping naver blog, Sleep 1 hour")
                time.sleep(3600)
                
            raise e
            
    def _update_blog_info(self, blogid, save_path, checkpoint):
        """Update the blog_info.csv file to mark a blog as processed"""
        blog_info_path = os.path.join(self.cache_dir, "blog_info.csv")
        
        try:
            blog_info = pd.read_csv(blog_info_path, index_col=0)
        except:
            blog_info = pd.DataFrame(columns=["blogid", "save_path", "checkpoint"])
            
        # Check if blogid already exists
        if blogid in blog_info["blogid"].values:
            # Update existing entry
            idx = blog_info.index[blog_info["blogid"] == blogid][0]
            blog_info.at[idx, "save_path"] = save_path
            blog_info.at[idx, "checkpoint"] = checkpoint
        else:
            # Add new entry
            new_data = {"blogid": [blogid], "save_path": [save_path], "checkpoint": [checkpoint]}
            blog_info = pd.concat([blog_info, pd.DataFrame(new_data)], ignore_index=True)
            
        # Save updated dataframe
        blog_info.to_csv(blog_info_path)