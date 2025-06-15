import os
import json


class NaverCafe():
    def __init__(self, name, cafe_id, member_count):
        self.name = name
        self.cafe_id = cafe_id
        self.member_count = member_count


def main():
    data_dir = os.path.join("data", "navercafe_id")
    config_path = os.path.join("configs", "navercafe", "navercafe_id.tsv")
    cafes = {}
    if os.path.exists(config_path):
        with open(config_path) as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                parts = line.split("\t")
                if len(parts) == 3:
                    if parts[0] == "cafe_id":
                        continue
                    cafe_id, name, member_count = parts
                    cafes[cafe_id] = NaverCafe(
                        name, cafe_id, int(member_count))

    cafes = {}
    jsonl_files = [f for f in os.listdir(data_dir) if f.endswith('.jsonl')]
    for jsonl_file in jsonl_files:
        file_path = os.path.join(data_dir, jsonl_file)
        with open(file_path, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    cafe_data = json.loads(line)
                    cafes[cafe_data["cafe_id"]] = NaverCafe(
                        cafe_data["cafe_name"],
                        cafe_data["cafe_id"],
                        int(cafe_data["cafe_member"].replace(",", ""))
                    )
                except json.JSONDecodeError as e:
                    print(f"Error decoding JSON from line: {line}, Error: {e}")

    with open(config_path, 'w', encoding='utf-8') as f:
        f.write("cafe_id\tname\tmember_count\n")
        for cafe_id, cafe in cafes.items():
            f.write(f"{cafe.cafe_id}\t{cafe.name}\t{cafe.member_count}\n")


if __name__ == "__main__":
    main()
