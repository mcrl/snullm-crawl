import os
from typing import List


def count_file_lines(filepath: str) -> int:
    with open(filepath, "r", encoding="utf-8") as f:
        return len(f.readlines())


def read_tsv(filepath: str, header=True) -> List[str]:
    with open(filepath, "r", encoding="utf-8") as f:
        if header:
            f.readline()
        lines = f.readlines()
        return [line.strip().split("\t") for line in lines if line.strip()]


def read_txt(filepath: str, header=True) -> List[str]:
    with open(filepath, "r", encoding="utf-8") as f:
        if header:
            f.readline()
        lines = f.readlines()
        return [line.strip() for line in lines if line.strip()]
