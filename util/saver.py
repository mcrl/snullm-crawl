import os
from util.aggregator import JsonAggregator
from util.custom_logger import setup_logger


def saver_routine(save_dir, save_id, save_queue, exception_queue, log_path):
    logger = setup_logger(log_path, "saver")
    aggregator = JsonAggregator(save_dir, save_id, logger)

    error_count = 0
    while True:
        try:
            document = save_queue.get()
            if document is None:
                logger.info("Received None. Exiting saver_routine")
                break
            aggregator.write(document)
        except Exception as e:
            error_count += 1
            logger.error(f"Error in saver_routine: {e}")
            if error_count > 10:
                logger.error("Too many errors. Exiting saver_routine")
                exception_queue.put(e)
                break
