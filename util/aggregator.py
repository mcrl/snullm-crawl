import os
import os.path as osp

from logging import Logger


class JsonAggregator:
    save_dir = None
    save_filename = None
    save_id = None
    document_count_in_file = 0
    file_count_in_dir = 0
    file_io = None
    logger = None

    def __init__(self, save_dir: str, save_id: str, logger: Logger, reset=False):
        self.logger = logger
        self.save_dir = save_dir
        self.save_id = save_id

        logger.info("Start JsonAggregator")

        # count jsonl files in the directory
        jsonl_files = [
            osp.join(save_dir, f)
            for f in os.listdir(save_dir)
            if osp.isfile(osp.join(save_dir, f))
            and f.startswith(save_id)
            and f.endswith(".jsonl")
        ]
        if reset and len(jsonl_files) > 0:
            logger.info("Resetting JsonAggregator")
            for f in jsonl_files:
                if osp.isfile(f):
                    os.remove(f)
            jsonl_files = []
        self.file_count_in_dir = len(jsonl_files)
        logger.info(f"file_count_in_dir: {self.file_count_in_dir}")
        # if there is no file, create one
        self.__set_save_filename()
        if self.file_count_in_dir == 0:
            self.proceed_to_the_next_file()
        elif self.need_to_proceed_to_the_next_file():
            self.proceed_to_the_next_file()
        msg = f"JsonAggregator: {self.save_filename}"
        logger.info(msg)

    def __del__(self):
        if self.file_io is not None:
            self.file_io.close()
        self.file_io = None

    def write(self, document_line, newline=True):
        if self.file_io is None:
            self.file_io = open(self.save_filename, "a")
        if not document_line:
            return
        self.file_io.write(document_line)
        if newline:
            self.file_io.write("\n")
        self.document_count_in_file += 1
        if (
            self.document_count_in_file % 1000
            and self.need_to_proceed_to_the_next_file()
        ):
            self.proceed_to_the_next_file()

    def proceed_to_the_next_file(self):
        if self.file_io is not None:
            self.file_io.close()
        self.file_count_in_dir += 1

        self.__set_save_filename()
        msg = f"save_filename: {self.save_filename}"
        self.logger.info(msg)

        self.file_io = open(self.save_filename, "a")
        self.document_count_in_file = 0
        self.logger.info(f"JsonAggregator: {self.save_filename}")

    def need_to_proceed_to_the_next_file(self):
        file_size = osp.getsize(self.save_filename)

        # criteria: 100MiB
        return file_size > 100 * 1024 * 1024

    def __set_save_filename(self):
        self.save_filename = osp.join(
            self.save_dir,
            f"{self.save_id}_{str(self.file_count_in_dir).zfill(5)}.jsonl",
        )
