from concurrent.futures import ThreadPoolExecutor
import time
import requests
from bs4 import BeautifulSoup
from csv_file import CsvWriter
from file_listing import FileDescriptor
from files_logging import Log
from settings import Settings

class WebRequestHandler:

    rate_limited = False

    def __init__(self, logger:Log, parser:PaginationParsingHandler, failed_links_csv_writer:CsvWriter):
        self.logger = logger
        self._pool = ThreadPoolExecutor(max_workers=12)
        self.parser = parser
        self.failed_links_csv_writer = failed_links_csv_writer

    def error_watcher(self):
        while True:
            if(self.rate_limited):
                self.logger.log("Rate limited! Pausing requests for 5 minutes...")
                #TODO: Pause the requests
                time.sleep(300)
                self.rate_limited = False
            time.sleep(5)

    def submit_pagination_url(self, dataset_index, page_index, url, on_parse_complete):
        return self._pool.submit(self._poll_pagination_url_thread, dataset_index, page_index, url, on_parse_complete)

    def _poll_pagination_url_thread(self, dataset_index, page_index, url, on_parse_complete=None):
        response = requests.get(url, headers=Settings.headers)

        if(response.ok):
            self.parser.submit_data(dataset_index, page_index, str(response.text), on_parse_complete) #Create a copy of the text data so the parser can handle it faster
        elif(response.status_code == 404):
            self.logger.log(f"URL {url} not found (404). Skipping...")
            self.failed_links_csv_writer.rows_queue.put({'dataset_index': dataset_index, 'page_index': page_index, 'http_status_code': 404})
        elif(response.status_code == 429):
            self.rate_limited = True
            self.logger.log(f"Rate limited on URL {url}. Resubmitting and pausing pagination...")
            self.submit_pagination_url(dataset_index, page_index, url, on_parse_complete)   #Resubmit the URL so it will be processed after the pause
        else:
            self.logger.log(f"Unhandled status code {response.status_code} on URL {url}")
            self.failed_links_csv_writer.rows_queue.put({'dataset_index': dataset_index, 'page_index': page_index, 'http_status_code': response.status_code})

class PaginationParsingHandler:

    def __init__(self, logger:Log):
        self.logger = logger
        self._pool = ThreadPoolExecutor(max_workers=6)

    def submit_data(self, dataset_index, page_index, document:str, on_parse_complete):
        return self._pool.submit(self._parse_document_thread, dataset_index, page_index, document, on_parse_complete)
    
    def _parse_document_thread(self, dataset_index, page_index, document:str, on_parse_complete):
        links_metadata:list[FileDescriptor] = []

        soup = BeautifulSoup(document, 'html.parser')
        content_items = soup.find_all("span", class_="field-content")
        links = []
        for content in content_items:
            links.append(content.contents[0])

        for link in links:  #Iterate through each link and pull the name, then add it to our list
            full_file_name = link.string
            full_link = f"{link['href']}"
            split_file = full_file_name.split('.')
            file_name = split_file[0]
            file_type = split_file[1]
            sequence_number = int(file_name[4:12])   #Should be 8 numbers succeeding EFTA, converted to an int, so it will strip leading 0s

            links_metadata.append(FileDescriptor(dataset_index, page_index, sequence_number, file_type, full_link))

        on_parse_complete(links_metadata)