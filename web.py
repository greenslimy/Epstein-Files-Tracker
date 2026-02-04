from concurrent.futures import (
    ThreadPoolExecutor, 
    Future
)
import requests
from bs4 import BeautifulSoup
from file_listing import FileMetadata

class LivePaginationHandler:

    rate_limited = False

    def __init__(self, live_pages_url_base):
        self.live_pages_url_base = live_pages_url_base
        self._pool = ThreadPoolExecutor(max_workers=8)
        self._parser = _PaginationParsingHandler()

    def submit_pages(self, dataset, batch_index, page_batch:list[int]):
        return self._pool.submit(self._poll_pages_thread, dataset.dataset_index, batch_index, page_batch)

    def _poll_pages_thread(self, dataset_index, batch_index, page_batch:list[int]):
        pages_submitted:list[int] = []
        polled_pages:dict[int, str] = {}
        failed_pages:dict[int, PageFailure] = {}

        for page_index in page_batch:
            live_paginated_url = f"{self.live_pages_url_base}/data-set-{dataset_index}-files?page={page_index}"
            page_list_data = requests.get(live_paginated_url, headers={
                "sec-ch-ua": """"Brave";v="143", "Chromium";v="143", "Not A(Brand";v="24""",
                "sec-ch-ua-mobile":"?0",
                "sec-ch-ua-platform":"Windows",
                "upgrade-insecure-requests":"1",
                "user-agent":"Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/143.0.0.0 Safari/537.36"
            })
            pages_submitted.append(page_index)

            if(page_list_data.ok):
                polled_pages[page_index] = str(page_list_data.text) #Create a copy of the text data so the parser can handle it faster
            elif(page_list_data.status_code == 429):
                failed_pages[page_index] = PageFailure(page_index, 'rate_limited', "Rate Limited")
            else:
                failed_pages[page_index] = PageFailure(page_index, 'unknown', f"Unhandled status code {page_list_data.status_code} ({live_paginated_url})")

        return PageBatch(batch_index, pages_submitted, self._parser.submit_documents(polled_pages), failed_pages)

class PageBatch:

    def __init__(self, batch_index:int, pages_submitted:list[int], parsed_pages:Future[dict[int, list[FileMetadata]]], failed_pages:dict[int, PageFailure]):
        self.batch_index = batch_index
        self.pages_submitted = pages_submitted
        self.parsed_pages = parsed_pages
        self.failed_pages = failed_pages

class PageFailure:

    def __init__(self, page_index, fail_code, fail_reason):
        self.page_index = page_index
        self.failure_code = fail_code
        self.failure_reason = fail_reason

class _PaginationParsingHandler:

    def __init__(self):
        self._pool = ThreadPoolExecutor(max_workers=5)

    def submit_documents(self, documents:dict[int, str]):
        return self._pool.submit(self._parse_documents_thread, documents)
    
    def _parse_documents_thread(self, documents:dict[int, str]):
        links_metadata:dict[int, list[FileMetadata]] = {}

        for page_index, page_data in documents.items():
            document_links_metadata = []

            soup = BeautifulSoup(page_data, 'html.parser')
            content_items = soup.find_all("span", class_="field-content")
            links = []
            for content in content_items:
                links.append(content.contents[0])

            for link in links:  #Iterate through each link and pull the name, then add it to our list
                full_file_name = link.string
                full_link = f"https://justice.gov{link['href']}"
                split_file = full_file_name.split('.')
                file_name = split_file[0]
                file_type = split_file[1]
                sequence_number = int(file_name[4:12])   #Should be 8 numbers succeeding EFTA, converted to an int, so it will strip leading 0s

                document_links_metadata.append(FileMetadata(page_index, sequence_number, file_type, full_link))
            
            links_metadata[page_index] = document_links_metadata

        return links_metadata