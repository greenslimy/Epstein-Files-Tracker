import time
from files_logging import Log
import csv
from queue import Queue
from settings import Settings

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
            time.sleep(8)

            rows_to_write = self.rows_queue.qsize() #Recalculate number of rows to write after sleep

        self.csv_file.close()
        self.logger.log(f"Wrote detail file to {self.csv_file.name}")

    def close(self):
        self.program_completed = True