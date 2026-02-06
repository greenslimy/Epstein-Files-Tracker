from queue import Queue
import time
from datetime import datetime

class Log:
    program_completed = False

    def __init__(self, log_files_location, program_name):
        self.logs_queue = Queue()

        try:
            self.log_file = open(f"{log_files_location}/logs/{program_name}.log", "x")
        except FileExistsError:
            self.log_file = open(f"{log_files_location}/logs/{program_name}.log", "w")

        print(f"Writing log output to {self.log_file.name}")

    def append_logs_thread(self):
        num_logs_queued = 0

        while not self.program_completed or num_logs_queued > 0:
            for _ in range(num_logs_queued):
                self.log_file.write(f"[{datetime.now()}] {self.logs_queue.get()}\n")
            self.log_file.flush()
            time.sleep(5)

            num_logs_queued = self.logs_queue.qsize()   #Recalculate number of logs to write after sleep

        self.log_file.write(f"[{datetime.now()}] Process completed. End of log.")
        self.log_file.flush()
        self.log_file.close()

    def log(self, log_text:str):
        self.logs_queue.put(log_text)

    def close(self):
        self.program_completed = True