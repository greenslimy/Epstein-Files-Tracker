from queue import Queue
from csv_file import CsvWriter
from files_logging import Log
from file_listing import FileDescriptor
from web import LivePaginationHandler
from settings import Settings

class Dataset:

    def __init__(self, index):
        self.completed_pages = Queue[int]()   #Pages that have been fully paginated and parsed
        self.count_dataset_pages = Settings.dataset_pages[index]
        self.index = index

    def paginate(self, paginator:LivePaginationHandler, successful_links_csv_writer:CsvWriter):
        for page_index in range(self.count_dataset_pages):
            live_paginated_url = f"{Settings.live_paginated_base_url}/data-set-{self.index}-files?page={page_index}"
            paginator.submit_url(self.index, page_index, live_paginated_url, lambda links_metadata, page_index=page_index: self._on_page_parsed(page_index, links_metadata, successful_links_csv_writer))

    def _on_page_parsed(self, page_index, links_metadata:list[FileDescriptor], successful_links_csv_writer:CsvWriter):
        for metadata in links_metadata:
            metadata.page_index = page_index
            successful_links_csv_writer.rows_queue.put(metadata.get_row_data())
        self.completed_pages.put(page_index)
        self.logger.log(f"Dataset {self.index} page {page_index} parsed with {len(links_metadata)} links.")

    def get_count_completed_pages(self):
        return self.completed_pages.qsize()
    
    def set_logger(self, logger:Log):
        self.logger = logger