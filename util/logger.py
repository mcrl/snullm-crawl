import logging
import os
import time


def setup_logger(log_name):
    logger = logging.getLogger("io")
    logger.setLevel(logging.INFO)
    formatter = logging.Formatter(
        "[%(asctime)s] [" + log_name + "] %(levelname)s: %(message)s",
        "%Y-%m-%d %H:%M:%S",
    )
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    console_handler.setLevel(logging.WARNING)
    logger.addHandler(console_handler)
    date_time = time.strftime("%Y%m%d-%H%M%S")
    if not os.path.exists("logs"):
        os.makedirs("logs")
    file_handler = logging.FileHandler(f"logs/{date_time}-{log_name}.log")
    file_handler.setFormatter(formatter)
    file_handler.setLevel(logging.INFO)
    logger.addHandler(file_handler)

    return logger
