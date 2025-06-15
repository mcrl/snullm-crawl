"""miscellaneous utility functions"""
from typing import Dict, Any

DEFAULT_INTERVAL = 1


def get_backup(
    key: str, primary: Dict[str, Any], secondary: Dict[str, Any], default_value=None
):
    return primary.get(key, secondary.get(key, default_value))


def get_interval(shared, private):
    """Finds interval from two dictionaries. Use default value if not found"""
    return get_backup("interval", shared, private, default_value=DEFAULT_INTERVAL)
