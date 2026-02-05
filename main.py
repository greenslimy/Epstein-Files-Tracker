import threading
from csv_file import CsvWriter
from dataset import Dataset
import watchdog
from files_logging import Log
import csv
from web import LivePaginationHandler
import argparse
from settings import Settings

datasets:list[Dataset] = []

def main():
    argument_parser = argparse.ArgumentParser(formatter_class=argparse.RawTextHelpFormatter, description="Epstein Files Tracker")
    argument_parser.add_argument('-o', dest="tracker_output", type=str, help="Local location you would like output files to be written. Be sure to create a logs directory first!\nTracker will look here for input .csv files that were created by this program.", required=True)
    argument_parser.add_argument('-f', dest="epstein_files", type=str, help="Local location of your copy of the unzipped Epstein Files (Under construction)")
    argument_parser.add_argument('--paginate', action="store_true", help="Paginate and record links from the justice.gov live release of the files")
    arguments = argument_parser.parse_args()

    Settings.local_output_files_url = arguments.tracker_output
    Settings.local_files_base_url = arguments.epstein_files

    #Initialize datasets
    for set_index in range(Settings.dataset_count):
        #if(Settings.dataset_pages[set_index+1] > 10): Settings.dataset_pages[set_index+1] = 10    #TODO: Debug clamp
        datasets.append(Dataset(Settings.live_paginated_base_url, Settings.live_files_base_url, set_index+1))
    print(f"Initialized {len(datasets)} datasets")

    if(arguments.paginate):
        paginate()

    print("Program finished")

def paginate():
    process_name = "live_links_raw"

    logger = Log(Settings.local_output_files_url, process_name)
    logging_thread = threading.Thread(target=logger.append_logs)
    logging_thread.start()

    pagination_handler = LivePaginationHandler(Settings.live_paginated_base_url)

    csv_writer = CsvWriter(logger, process_name, ['dataset_index', 'page_index', 'sequence_number', 'file_type', 'public_link'])
    csv_writer_thread = threading.Thread(target=csv_writer.append_csv_thread)

    pagination_watchdog = watchdog.Pagination(logger, pagination_handler, datasets)
    pagination_watchdog_thread = threading.Thread(target=pagination_watchdog.update)   #Keeps track of each dataset thread's progress and updates the console
    
    pagination_watchdog_thread.start()
    for set_index in range(Settings.dataset_count):
        dataset_thread = datasets[set_index].create_pagination_thread(logger, pagination_handler)
        dataset_thread.start()
        dataset_thread.join()           #Wait for each dataset to finish before moving on to the next one
    pagination_watchdog_thread.join()   #Wait for the watchdog to confirm all datasets have been paginated before continuing

    count_pages = 0
    count_files = 0
    for set_index in range(Settings.dataset_count):
        count_pages += datasets[set_index].count_dataset_pages
        count_files += datasets[set_index].get_file_count()
    logger.log(f"Pagination completed - {count_files} links in {count_pages} pages across {Settings.dataset_count} datasets")

    #  Sort the datasets. This will make it easier to clean them later  #
    print("Sorting all dataset files...")
    for set_index in range(Settings.dataset_count):
        dataset_metadata_list = datasets[set_index].file_metadata_list[::]
        datasets[set_index].file_metadata_list = sorted(dataset_metadata_list, key=lambda metadata:metadata.sequence)
    
    csv_writer_thread.start()
    for set_index in range(Settings.dataset_count):
        for metadata in datasets[set_index].file_metadata_list:
            csv_writer.rows_queue.put({
                'dataset_index': set_index+1,
                'page_index': metadata.page_index,
                'sequence_number': metadata.sequence,
                'file_type': metadata.type,
                'public_link': metadata.public_link
            })

    csv_writer.close()
    print("Finished buffering live links file. Waiting for writer thread to complete...")
    csv_writer_thread.join()    #Wait for csv writing to complete
    
    logger.log("REMINDER: This file will likely contain many duplicates. This is how they were presented on the live justice.gov website.")

    logger.close()
    print("Finished buffering log file. Waiting for writer thread to complete...")
    logging_thread.join()

    print("\nREMINDER: This file will likely contain many duplicates. This is how they were presented on the live justice.gov website.")

if __name__ == '__main__':
    main()