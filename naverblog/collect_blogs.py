import requests
from bs4 import BeautifulSoup
import json
import yaml
import time
import tqdm
import sys
import os
import logging
import http.client
import subprocess
import re
import gzip
import argparse
import random
from concurrent.futures import ThreadPoolExecutor, as_completed
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from util.env import get_iplist
from filelock import FileLock

def parse_args():
    parser = argparse.ArgumentParser(description='Collect Naver Blog IDs')
    parser.add_argument('--config', type=str, required=True, help='Path to the configuration file')
    return parser.parse_args()

def load_config(config_path):
    with open(config_path, 'r') as f:
        config = yaml.safe_load(f)
    return config

def load_blog_list(path):
    try:
        lock_path = path + '.lock'
        with FileLock(lock_path):
            if os.path.exists(path):
                with open(path, 'r') as f:
                    return json.load(f)
            else:
                os.makedirs(os.path.dirname(path), exist_ok=True)
                return []
    except Exception as e:
        print(f"Error loading blog list: {e}")
        return []

def save_blog_list(blog_list, path):
    lock_path = path + '.lock'
    with FileLock(lock_path):
        with open(path, 'w') as f:
            json.dump(blog_list, f)
    print(f"Saved {len(blog_list)} blogs to {path}")

def load_visited_list(path):
    try:
        lock_path = path + '.lock'
        with FileLock(lock_path):
            if os.path.exists(path):
                with open(path, 'r') as f:
                    return json.load(f)
            else:
                os.makedirs(os.path.dirname(path), exist_ok=True)
                return []
    except Exception as e:
        print(f"Error loading visited list: {e}")
        return []

def save_visited_list(visited_list, path):
    lock_path = path + '.lock'
    with FileLock(lock_path):
        with open(path, 'w') as f:
            json.dump(visited_list, f)
    print(f"Saved {len(visited_list)} visited blogs to {path}")

def collect_neighbors(blogid, ip, interval=1):
    headers = {
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,/;q=0.8,application/signed-exchange;v=b3;q=0.7",
        "Accept-Encoding": "gzip, deflate, br",
        "Accept-Language": "ko,en-US;q=0.9,en;q=0.8,ja;q=0.7",
        "Cache-Control": "max-age=0",
        "Cookie": "",
        "Referer": "",
        "Sec-Ch-Ua": '"Not.A/Brand";v="8", "Chromium";v="114", "Google Chrome";v="114"',
        "Sec-Ch-Ua-Mobile": "?0",
        "Sec-Ch-Ua-Platform": "Windows",
        "Sec-Fetch-Dest": "document",
        "Sec-Fetch-Mode": "navigate",
        "Sec-Fetch-Site": "same-origin",
        "Sec-Fetch-User": "?1",
        "Upgrade-Insecure-Requests": "1",
        "user-agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/114.0.0.0 Safari/537.36"
    }
    
    try:
        conn = None
        try:
            conn = http.client.HTTPSConnection("m.blog.naver.com", 443, source_address=(ip, 0))
            
            headers["Referer"] = f"https://m.blog.naver.com/{blogid}/"
            path = f"/BuddyList.naver?blogId={blogid}"
            conn.request('GET', path, headers=headers)
            
            resp = conn.getresponse()
            
            if resp.status != 200:
                print(f"Error status {resp.status} for blog {blogid} using IP {ip}")
                if resp.status == 429:  # Too many requests
                    print(f"IP {ip} is rate limited. Waiting longer...")
                    time.sleep(interval * 5)  # Wait longer for rate limit
                return []
                
            cookie = resp.getheader("Set-Cookie")
            
            try:
                headers["Cookie"] = cookie[:cookie.find(";")] if cookie else ""
            except:
                headers["Cookie"] = ""
                
            encoding = resp.getheader("Content-Encoding")
            
            if encoding == "gzip":
                data = gzip.decompress(resp.read())
            else:
                data = resp.read()
                
            soup = BeautifulSoup(data, 'html.parser')
            nbr_list = [a['href'].split("/")[-1] for a in soup.find_all('a') if 'href' in a.attrs]
            
            processed_nbr_list = []
            for nbr in nbr_list:
                if "PostList.naver?blogId=" in nbr:
                    match = re.search(r"blogId=([^&]+)", nbr)
                    if match:
                        processed_nbr_list.append(match.group(1))
                elif "naver.com" not in nbr and "PostView.naver" not in nbr and len(nbr) > 0:
                    processed_nbr_list.append(nbr)
            
            time.sleep(interval)
            return processed_nbr_list
        finally:
            if conn:
                conn.close()
    except Exception as e:
        print(f"Error collecting neighbors for blog {blogid} using IP {ip}: {e}")
        time.sleep(interval)
        return []

def worker(worker_id, blogids, ip, interval, blog_list_path, visited_list_path, save_frequency=100):
    print(f"Worker {worker_id} starting with IP {ip}, processing {len(blogids)} blogs")
    
    all_blogs = load_blog_list(blog_list_path)
    visited_blogs = load_visited_list(visited_list_path)
    
    local_new_blogs = []
    local_visited_blogs = []
    processed_count = 0
    error_count = 0
    
    # Filter out already visited blogs
    blogs_to_process = [blog for blog in blogids if blog not in visited_blogs]
    print(f"Worker {worker_id}: {len(blogs_to_process)}/{len(blogids)} blogs need processing (others already visited)")
    
    for i, blogid in enumerate(blogs_to_process):
        if i % 10 == 0:
            print(f"Worker {worker_id}: Processing blog {i+1}/{len(blogs_to_process)}")
        
        # Mark this blog as visited
        local_visited_blogs.append(blogid)
        
        # Collect neighbors
        neighbors = collect_neighbors(blogid, ip, interval)
        
        if not neighbors:
            error_count += 1
            if error_count > 5:
                print(f"Worker {worker_id}: Too many consecutive errors, trying longer delay")
                time.sleep(interval * 10)  # Wait longer after multiple errors
                error_count = 0
            continue
        else:
            error_count = 0
            
        # Add new blogs to the local list
        new_blogs = [blog for blog in neighbors if blog not in all_blogs and blog not in local_new_blogs]
        if new_blogs:
            local_new_blogs.extend(new_blogs)
            
        processed_count += 1
            
        # Save periodically
        if processed_count % save_frequency == 0:
            # Save the blog list - reload first to avoid conflicts with other workers
            all_blogs = load_blog_list(blog_list_path)
            really_new_blogs = [blog for blog in local_new_blogs if blog not in all_blogs]
            if really_new_blogs:
                all_blogs.extend(really_new_blogs)
                save_blog_list(all_blogs, blog_list_path)
                print(f"Worker {worker_id}: Added {len(really_new_blogs)} new blogs")
                local_new_blogs = []
            
            # Save the visited list - reload first to avoid conflicts
            visited_blogs = load_visited_list(visited_list_path)
            really_new_visited = [blog for blog in local_visited_blogs if blog not in visited_blogs]
            if really_new_visited:
                visited_blogs.extend(really_new_visited)
                save_visited_list(visited_blogs, visited_list_path)
                print(f"Worker {worker_id}: Added {len(really_new_visited)} blogs to visited list")
                local_visited_blogs = []
            
            print(f"Worker {worker_id}: Processed {processed_count}/{len(blogs_to_process)}")
    
    # Final save for blog list
    if local_new_blogs:
        all_blogs = load_blog_list(blog_list_path)
        really_new_blogs = [blog for blog in local_new_blogs if blog not in all_blogs]
        if really_new_blogs:
            all_blogs.extend(really_new_blogs)
            save_blog_list(all_blogs, blog_list_path)
            print(f"Worker {worker_id}: Final save - added {len(really_new_blogs)} new blogs")
    
    # Final save for visited list
    if local_visited_blogs:
        visited_blogs = load_visited_list(visited_list_path)
        really_new_visited = [blog for blog in local_visited_blogs if blog not in visited_blogs]
        if really_new_visited:
            visited_blogs.extend(really_new_visited)
            save_visited_list(visited_blogs, visited_list_path)
            print(f"Worker {worker_id}: Final save - added {len(really_new_visited)} blogs to visited list")
    
    return processed_count

def main():
    args = parse_args()
    config = load_config(args.config)
    
    ips = config.get("ips")
    interval = config.get('default_interval', 1)
    blog_list_path = config.get('bloglist_path', 'cache/naverblog/bloglist.json')
    
    # Derive visited list path from blog list path
    visited_list_path = os.path.join(
        os.path.dirname(blog_list_path),
        'visited_bloglist.json'
    )
    
    # Ensure paths are absolute
    if not os.path.isabs(blog_list_path):
        blog_list_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', blog_list_path)
    
    if not os.path.isabs(visited_list_path):
        visited_list_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', visited_list_path)
    
    # Create directories if they don't exist
    os.makedirs(os.path.dirname(blog_list_path), exist_ok=True)
    
    # Load the blog list and visited list
    blog_list = load_blog_list(blog_list_path)
    visited_list = load_visited_list(visited_list_path)
    
    print(f"Loaded {len(blog_list)} blogs from {blog_list_path}")
    print(f"Loaded {len(visited_list)} visited blogs from {visited_list_path}")
    
    # If blog list is empty, add some seed blogs
    if not blog_list:
        print("Empty bloglist. Exiting.")
        return
    
    # Filter out blogs that have already been visited
    unvisited_blogs = [blog for blog in blog_list if blog not in visited_list]
    print(f"Found {len(unvisited_blogs)} unvisited blogs out of {len(blog_list)} total blogs")
    
    # Split work among available IPs
    num_ips = len(ips)
    if num_ips == 0:
        print("No IPs available. Exiting.")
        return
    
    print(f"Starting collection with {num_ips} IPs, processing {len(unvisited_blogs)} unvisited blogs")
    
    blogs_per_ip = len(unvisited_blogs) // num_ips
    remainder = len(unvisited_blogs) % num_ips
    
    blog_chunks = []
    start = 0
    for i in range(num_ips):
        chunk_size = blogs_per_ip + (1 if i < remainder else 0)
        blog_chunks.append(unvisited_blogs[start:start+chunk_size])
        start += chunk_size
    
    # Process blogs using multiple workers (one per IP)
    with ThreadPoolExecutor(max_workers=num_ips) as executor:
        futures = []
        for i, (chunk, ip) in enumerate(zip(blog_chunks, ips)):
            save_frequency = min(100, max(10, len(chunk) // 10))  # Dynamic save frequency
            future = executor.submit(
                worker, 
                i+1, 
                chunk, 
                ip, 
                interval, 
                blog_list_path, 
                visited_list_path,
                save_frequency
            )
            futures.append(future)
        
        # Collect results
        total_processed = 0
        for future in as_completed(futures):
            total_processed += future.result()
    
    # Final stats
    final_blog_list = load_blog_list(blog_list_path)
    final_visited_list = load_visited_list(visited_list_path)
    
    print(f"Finished collection. Total blogs in list: {len(final_blog_list)}")
    print(f"Total visited blogs: {len(final_visited_list)}")
    print(f"Processed {total_processed} blogs in this run")
    print(f"Blogs yet to visit: {len(final_blog_list) - len(final_visited_list)}")

if __name__ == "__main__":
    main()
