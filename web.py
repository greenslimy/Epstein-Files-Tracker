from concurrent.futures import Future, ThreadPoolExecutor
import time
import requests
from bs4 import BeautifulSoup
from csv_file import CsvWriter
from files_logging import Log
from settings import Settings

class WebRequestHandler:

    rate_limited = False

    def __init__(self, logger:Log, parser, failed_csv_writer:CsvWriter):
        self.logger = logger
        self._pool = ThreadPoolExecutor(max_workers=12)
        self.parser = parser
        self.failed_csv_writer = failed_csv_writer

    def error_watcher(self):
        while True:
            if(self.rate_limited):
                self.logger.log("Rate limited! Pausing requests for 5 minutes...")
                #TODO: Pause the requests
                time.sleep(300)
                self.rate_limited = False
            time.sleep(5)

    def submit_url(self, url, on_parse_complete) -> Future[DownloadStatus]:
        return self._pool.submit(self._poll_url_thread, url, on_parse_complete)

    def _poll_url_thread(self, url, on_parse_complete=None):
        response = requests.get(url, headers=Settings.headers, cookies=Settings.cookie)

        if(response.ok):
            if(type(self.parser) is PaginationParsingHandler):
                self.parser.submit_data(response.text, on_parse_complete)
            else:
                if(on_parse_complete is not None):
                    return on_parse_complete(response.content)
        elif(response.status_code == 404):
            self.logger.log(f"URL {url} not found (404). Skipping...")
            self.failed_csv_writer.rows_queue.put({'url': url, 'http_status_code': 404})
            return DownloadStatus(url, 404)
        elif(response.status_code == 429):
            self.rate_limited = True
            self.logger.log(f"Rate limited on URL {url}. Resubmitting and pausing requests...")
            self.submit_url(url, on_parse_complete)   #Resubmit the URL so it will be processed after the pause
            return DownloadStatus(url, 429)
        else:
            self.logger.log(f"Unhandled status code {response.status_code} on URL {url}")
            self.failed_csv_writer.rows_queue.put({'url': url, 'http_status_code': response.status_code})
            return DownloadStatus(url, response.status_code)
        
        return DownloadStatus(url, 400)

class DownloadStatus:
    def __init__(self, url:str, http_status_code:int):
        self.url = url
        self.http_status_code = http_status_code

class PaginationParsingHandler:

    def __init__(self, logger:Log):
        self.logger = logger
        self._pool = ThreadPoolExecutor(max_workers=6)

    def submit_data(self, document, on_parse_complete):
        return self._pool.submit(self._parse_document_thread, document, on_parse_complete)
    
    def _parse_document_thread(self, document, on_parse_complete):
        links_metadata:list[tuple[int, str, str]] = []

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

            links_metadata.append((sequence_number, file_type, full_link))

        on_parse_complete(links_metadata)