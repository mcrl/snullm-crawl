import os
import os.path as osp
import tqdm
import json
import multiprocessing as mp
from bs4 import BeautifulSoup
from tqdm import tqdm
import logging

from navernewsparser import parse_navernews_soup
from argument_validator import get_office
from aggregator import JsonAggregator
import random
import re
from math import ceil
from functools import partial

comment_ptrn = re.compile("<!--.*?-->", re.DOTALL)

IGNORES = [
    "imgtbl_start_",
    "imgtbl_end_",
    "imgsrc_start_",
    "imgsrc_end_",
    "cap_start_",
    "cap_end_",
    "SUB_TITLE_START",
    "SUB_TITLE_END",
]


def batch_check(batch, dirname=None, ending=None):
    batch_res = []

    for f in batch:
        f = osp.join(dirname, f)
        if ending and not f.endswith(ending):
            continue
        # skip directories
        if osp.isdir(f):
            continue
        batch_res.append(f)
    return batch_res


def find_file(dirname: str, ending=None):
    to_return = []
    print(f"Finding files in {dirname}")
    files = os.listdir(dirname)
    file_count = len(files)
    print(f"Found {file_count} files")
    if file_count == 0:
        return to_return
    workers = mp.cpu_count()
    batchsize = ceil(file_count / workers)
    batches = [files[i: i + batchsize]
               for i in range(0, len(files), batchsize)]
    check_fn = partial(batch_check, dirname=dirname, ending=ending)
    with mp.Pool(processes=workers) as p:
        mapped_batches = p.map(check_fn, batches)
    p.close()
    p.join()

    to_return = []
    for batch in mapped_batches:
        to_return.extend(batch)

    return to_return


def worker_routine(worker_id, html_files, office_name, oid):
    logger = logging.getLogger("__name__")
    handler = logging.StreamHandler()
    logger.addHandler(handler)
    aggr = JsonAggregator(
        "reparsed", f"{oid}_worker{worker_id}", logger, reset=True)
    for html_file in tqdm(html_files, disable=(worker_id != 0)):
        with open(html_file, "r") as f:
            text = f.read()
        # replace comments
        try:
            text = comment_ptrn.sub("", text)
            soup = BeautifulSoup(text, "html.parser")
            document = parse_navernews_soup(soup, logger, office_name)
            if document:
                aggr.write(document)
        except Exception as e:
            logger.error(
                f"Worker {worker_id} - Error while writing {html_file}: {e}")
            continue


def handle_office(oid):
    office = oid
    test_dir = f"data/navernews/{office}/htmls"
    office_name = get_office(office)
    print("=" * 80)
    print(f"Handling {oid}: {office_name}")
    print(f"Finding files for {office_name}")
    html_files = find_file(test_dir, ending=".html")

    print(f"Batching {office_name}")
    workers = 32

    batchsize = ceil(len(html_files) / workers)
    if batchsize == 0:
        print(f"Skipping {office_name}\n")
        return
    batches = [
        html_files[i: i + batchsize] for i in range(0, len(html_files), batchsize)
    ]

    print(f"Parsing {oid}: {office_name}")
    processes = []
    for i in range(workers):
        p = mp.Process(
            target=worker_routine,
            args=(i, batches[i], office_name, oid),
        )
        p.start()
        processes.append(p)

    for p in processes:
        p.join()
        if p.exitcode != 0:
            print(f"Worker {p.pid} exited with code {p.exitcode}")
            raise Exception(f"Worker {p.pid} exited with code {p.exitcode}")

    print(f"Finished {office_name}\n")


offices = os.listdir("data/navernews")
with open("cache/navernews/reparse.txt", "r") as f:
    already_processed = f.readlines()
for line in already_processed:
    skip_office = line.strip()
    if not skip_office:
        continue
    print(f"Skipping {skip_office}: {get_office(skip_office)}")
    offices.remove(skip_office)
offices.sort(key=lambda x: int(x), reverse=True)

with open("cache/navernews/reparse.txt", "w") as f:
    f.write("".join(already_processed))
    f.flush()
    for office in offices:
        handle_office(office)
        f.write(f"{office}\n")
        f.flush()
