import logging


def setup_logger(log_path, ip):
    logger = logging.getLogger("io")
    logger.setLevel(logging.INFO)
    formatter = logging.Formatter(
        "%(asctime)s:[" + ip +
        "]:%(levelname)s:%(message)s", "%Y-%m-%d %H:%M:%S"
    )
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    console_handler.setLevel(logging.WARNING)
    logger.addHandler(console_handler)
    file_handler = logging.FileHandler(log_path)
    file_handler.setFormatter(formatter)
    file_handler.setLevel(logging.INFO)
    logger.addHandler(file_handler)

    return logger
