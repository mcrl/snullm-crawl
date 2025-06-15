import subprocess
import re
import yaml
import os


def get_iplist():
    yaml_path = "configs/env.yml"
    if os.path.isfile(yaml_path):
        with open(yaml_path, "r") as file:
            data_dict = yaml.safe_load(file)
        ips = data_dict.get("ips", [])
        if ips:
            return ips
    try:
        completed = subprocess.run(
            ["ifconfig"],
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            text=True,
            check=True
        )
    except subprocess.CalledProcessError:
        return []

    output = completed.stdout.splitlines()
    ips = []
    iface_up = False
    docker0 = False
    for line in output:
        # “eth0: flags=4163<UP,…”
        if re.match(r'^[a-zA-Z0-9]+', line):
            iface_up = ("UP" in line)
            docker0 = re.match(r'^docker0', line) is not None
            continue

        if not iface_up:
            continue

        # example: “inet 192.168.0.10 ...”
        ip_match = re.search(r"inet\s+([\d\.]+)", line)
        if not ip_match:
            continue
        ip = ip_match.group(1)
        if not ip:
            continue

        if ip.startswith("127.") or ip.startswith("169.254."):
            continue

        if docker0:
            continue

        ips.append(ip)
    return ips


AVAILABLE_IPS = get_iplist()


def is_valid_ip(ip):
    return ip in AVAILABLE_IPS


def get_ip(index):
    return AVAILABLE_IPS[index]
