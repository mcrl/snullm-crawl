from typing import List, Tuple

from util.env import is_valid_ip


def parse_iplist(ip_args: List[str], default_interval=1) -> Tuple[List[str], List[int]]:
    def _handle_arg(argv: str, default_interval: int) -> Tuple[str, int]:
        if ":" in argv:
            ip, interval = argv.split(":")[:2]
            if not interval.isdigit():
                raise ValueError(f"Invalid interval {interval}")
            interval = int(interval)
        else:
            ip, interval = argv, default_interval
        if not is_valid_ip(ip):
            raise ValueError(f"Invalid ip {ip}")
        return ip, interval

    ips, intervals = [], []
    for arg in ip_args:
        ip, interval = _handle_arg(arg, default_interval)
        ips.append(ip)
        intervals.append(interval)
    return ips, intervals
