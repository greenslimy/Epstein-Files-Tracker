from dataset import Dataset
import sys
import time
from files_logging import Log
from web import LivePaginationHandler

class Pagination:

    watched_datasets:list[Dataset] = []

    def __init__(self, logger:Log, paginator:LivePaginationHandler, datasets):
        self.logger = logger
        self.paginator = paginator
        self.watched_datasets = datasets

    def update(self):
        completed_paginations = []

        count_watched_datasets = len(self.watched_datasets)
        self.logger.log(f"Starting page enumeration of {len(self.watched_datasets)} datasets")
        print(f"Enumerating {count_watched_datasets} paginated lists of files...")
        while len(completed_paginations) < count_watched_datasets:
            for dataset in self.watched_datasets:
                index = dataset.dataset_index

                if(dataset.get_raw_complete_pages_count() == dataset.count_dataset_pages):
                    if(index not in completed_paginations):
                        completed_paginations.append(index)
                    sys.stdout.write("\033[92m")
                sys.stdout.write(f"\x1b[2K Dataset {index} - {dataset.get_raw_complete_pages_count()}/{dataset.count_dataset_pages} pages - {dataset.get_raw_file_count()} links")
                if(self.paginator.rate_limited):
                    sys.stdout.write("\033[91m\tRATE LIMITED\033[0m")
                if(index < count_watched_datasets): sys.stdout.write("\n")

                sys.stdout.write("\033[0m\r")   #Clear any color and return to the beginning of the line
                sys.stdout.flush()

            if(len(completed_paginations) < count_watched_datasets):
                sys.stdout.write("\x1b[1A"*(count_watched_datasets-1))  #Move up x lines
            else:
                print("\nAll paginations complete! Waiting for this thread to end before continuing...")
                break
            time.sleep(5)