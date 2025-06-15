import os
import os.path as osp
import json
from glob import glob

pttn = "data/daumcafe_id/*.jsonl"

files = glob(pttn)
dest_path = "configs/daumcafe/daumcafe.txt"

# mkdir
if not osp.isdir(osp.dirname(dest_path)):
    os.makedirs(osp.dirname(dest_path), exist_ok=True)

with open(dest_path, "w") as f:
    for file in files:
        with open(file, "r") as infile:
            for line in infile:
                data = json.loads(line)
                cafeid = data.get("id")
                if cafeid:
                    f.write(f"{cafeid}\n")
                else:
                    print(f"Warning: No 'id' found in {file}")
print(f"Saved cafe IDs to {dest_path}")