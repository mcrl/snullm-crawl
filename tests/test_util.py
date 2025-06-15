from util.env import get_iplist
import pytest
import re


@pytest.fixture
def dummy_logger():
    from unittest.mock import Mock
    return Mock()


def test_get_iplist():
    ips = get_iplist()
    assert isinstance(ips, list)
    assert len(ips) > 0
    ip_pattern = re.compile(r"^\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}$")
    for ip in ips:
        assert isinstance(ip, str)
        assert ip_pattern.match(ip) is not None, f"Invalid IP format: {ip}"
