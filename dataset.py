from files_logging import Log
import threading
from file_listing import (
    FileMetadata
)
from web import (
    LivePaginationHandler,
    PageBatch,
    PageFailure
)
from concurrent.futures import (
    as_completed,
    Future
)
from settings import Settings

headers = {
    "sec-ch-ua": """"Brave";v="143", "Chromium";v="143", "Not A(Brand";v="24""",
    "sec-ch-ua-mobile":"?0",
    "sec-ch-ua-platform":"Windows",
    "upgrade-insecure-requests":"1",
    "user-agent":"Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/143.0.0.0 Safari/537.36"
}

class Dataset:

    def __init__(self, live_page_url_base, live_file_url_base, index):
        self.completed_pages:list[int] = []
        self.file_metadata_list:list[FileMetadata] = []
        self.live_paginated_url = f"{live_page_url_base}/data-set-{index}-files"
        self.live_files_url = f"{live_file_url_base}/DataSet {index}"
        self.dataset_index = index
        self.count_dataset_pages = Settings.dataset_pages[self.dataset_index]

    def paginate(self, logger:Log, paginator:LivePaginationHandler):
        batches_to_submit:dict[int, list[int]] = self._get_page_batches(5)
        submitted_batches:list[Future[PageBatch]] = []
        for batch_index, page_batch in batches_to_submit.items():
            submitted_batches.append(paginator.submit_pages(self, batch_index, page_batch))

        while self.get_complete_pages_count() < self.count_dataset_pages:

            for processed_batch in as_completed(submitted_batches):
                batch_result = processed_batch.result()             #Wait for the batch to finish reading each page
                parsed_pages = batch_result.parsed_pages.result()   #Wait for those pages in the batch to be parsed
                logger.log(f"Dataset {self.dataset_index} batch {batch_result.batch_index} processed - submitted: {len(batch_result.pages_submitted)} parsed: {len(parsed_pages)} failed: {len(batch_result.failed_pages)}")
                for parsed_page_index, links_metadata in parsed_pages.items():
                    self.file_metadata_list.extend(links_metadata)
                    self.completed_pages.append(parsed_page_index)

                for failed_page_index, failure_detail in batch_result.failed_pages.items():
                    logger.log(f"Dataset {self.dataset_index} page {failed_page_index} failed: {failure_detail.failure_code} - {failure_detail.failure_reason}.")

                    if(failure_detail.failure_code == 'rate_limited'):
                        paginator.rate_limited = True

        logger.log(f"Enumerated {self.get_file_count()} links over {self.count_dataset_pages} pages in public dataset {self.dataset_index}.")

    def _get_page_batches(self, num_pages:int):     #This could be done better, but Im lazy
        batches_to_submit:dict[int, list[int]] = {}
        num_batches = -(self.count_dataset_pages // -num_pages) #Upside down floor division

        for batch_index in range(num_batches):
            batch_pages:list[int] = []
            start_page_index = batch_index * num_pages
            end_page_index = start_page_index+num_pages
            if(end_page_index > self.count_dataset_pages):  #Clamp
                end_page_index = self.count_dataset_pages

            for page_index in range(start_page_index, end_page_index):
                batch_pages.append(page_index)

            batches_to_submit[batch_index] = batch_pages
        return batches_to_submit

    def get_file_count(self):
        return len(self.file_metadata_list)
    
    def get_complete_pages_count(self):
        return len(self.completed_pages)

    def create_pagination_thread(self, logger:Log, paginator:LivePaginationHandler):
        self.current_thread = threading.Thread(target=self.paginate, args=(logger,paginator,))
        return self.current_thread