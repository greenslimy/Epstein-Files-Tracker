import time
from files_logging import Log
import csv
from queue import Queue
from settings import Settings
from file_listing import CsvEntry, FileDescriptor
from typing import Generator, Generic, TypeVar

class CsvWriter:

    program_completed = False

    def __init__(self, logger:Log, csv_file_name:str, headers:list[str]):
        local_live_links_csv_path = f"{Settings.local_output_files_url}/{csv_file_name}.csv"
        self.logger = logger
        self.rows_queue = Queue()

        try:
            self.csv_file = open(local_live_links_csv_path, mode='x', newline='', encoding='utf-8')
        except FileExistsError:
            self.csv_file = open(local_live_links_csv_path, mode='w', newline='', encoding='utf-8')

        print(f"Writing process output to {local_live_links_csv_path}")
        self._writer = csv.DictWriter(self.csv_file, fieldnames=headers)
        self._writer.writeheader()

    def append_csv_thread(self):
        rows_to_write = 0

        while not self.program_completed or rows_to_write > 0:
            for _ in range(rows_to_write):
                self._writer.writerow(self.rows_queue.get())
            self.csv_file.flush()
            time.sleep(5)

            rows_to_write = self.rows_queue.qsize() #Recalculate number of rows to write after sleep

        self.csv_file.close()
        self.logger.log(f"Wrote detail file to {self.csv_file.name}")

    def close(self):
        self.program_completed = True

class CsvReader():

    def __init__(self, logger:Log, csv_file_name:str):
        local_live_links_csv_path = f"{Settings.local_output_files_url}/{csv_file_name}.csv"
        self.logger = logger

        try:
            self.csv_file = open(local_live_links_csv_path, mode='r', newline='', encoding='utf-8')
        except FileNotFoundError:
            self.logger.log(f"CSV file {local_live_links_csv_path} not found.")
            raise

        print(f"Reading process input from {local_live_links_csv_path}")
        self._reader = csv.DictReader(self.csv_file)    #Headers will be inferred from the first row

    def read_all_rows(self) -> Generator[FileDescriptor]:
        for row in self._reader:
            yield FileDescriptor.from_row_data(row)

    def read_rows_chunked(self, chunk_size:int) -> Generator[list[dict[str, str]]]:
        chunk:list[dict[str, str]] = []

        for row in self._reader:
            chunk.append(row)
            if(len(chunk) >= chunk_size):
                yield chunk
                chunk = []
        if(len(chunk) > 0):
            yield chunk

    def close(self):
        self.csv_file.close()