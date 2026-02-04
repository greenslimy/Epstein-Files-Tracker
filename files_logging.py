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
        

    def append_logs(self):
        num_logs_queued = 0

        while not self.program_completed or num_logs_queued > 0:
            num_logs_queued = self.logs_queue.qsize()

            for entry_index in range(num_logs_queued):
                log_entry = self.logs_queue.get()
                self.log_file.write(f"[{datetime.now()}] {log_entry}\n")
                self.log_file.flush()
            time.sleep(1)
        self.log_file.write(f"Program completed. End of log.")
        self.log_file.flush()
        self.log_file.close()

    def log(self, log_text:str):
        self.logs_queue.put(log_text)