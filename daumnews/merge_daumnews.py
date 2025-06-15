import os
import json
from datetime import datetime, timedelta

start = "20210101"
end = "20230630"

start_date = datetime.strptime(start, "%Y%m%d").date()
end_date = datetime.strptime(end, "%Y%m%d").date()

save_path = "data/daumnews/"
jsonl_path = "data/daumnews/jsonl/"

oids = os.listdir(save_path)
oids.remove("htmls")
oids.remove("jsonl")

filename = "00001.json"
path = os.path.join(jsonl_path, filename)
# filesize = 0.0
f = open(path, "w", encoding="utf-8")

while start_date <= end_date:
    fname = datetime.strftime(start_date, "%Y%m%d") + ".jsonl"
    print(f"Loading {fname}")
    for oid in oids:
        if not os.path.exists(os.path.join(save_path, oid, "jsonl", fname)):
            continue
        try:
            with open(os.path.join(save_path, oid, "jsonl", fname), 'r', encoding='utf-8') as f2:
                for line in f2:
                    f.write(line)
                    filesize = os.path.getsize(path) / (1000 * 1000)
                    if filesize > 100:
                        f.close()

                        filename = str(
                            (int(filename[:-5]) + 1)).zfill(5) + ".json"
                        path = os.path.join(jsonl_path, filename)

                        f = open(path, "w", encoding="utf-8")
        except:
            print(f"{oid} error")
            continue

    start_date += timedelta(days=1)
f.close()
