import threading
from csv_file import (
    CsvWriter,
    CsvReader
)
from dataset import Dataset
import watchdog
from files_logging import Log
import csv
from web import LivePaginationHandler
import argparse
from settings import Settings
from pathlib import Path

datasets:list[Dataset] = []

def main():
    argument_parser = argparse.ArgumentParser(formatter_class=argparse.RawTextHelpFormatter, description="Epstein Files Tracker")
    argument_parser.add_argument('-o', dest="tracker_output", type=str, help="Local location you would like output files to be written. Be sure to create a logs directory first!\nTracker will look here for input .csv files that were created by this program.", required=True)
    argument_parser.add_argument('-f', dest="epstein_files", type=str, help="Local location of your copy of the unzipped Epstein Files (Under construction)")
    argument_parser.add_argument('--paginate', action="store_true", help="Paginate and record links from the justice.gov live release of the files")
    argument_parser.add_argument('--cleanup', action="store_true", help="Clean up duplicates and sort links from a previously generated live_links_raw.csv file")
    arguments = argument_parser.parse_args()

    Settings.local_output_files_url = arguments.tracker_output
    Settings.local_files_base_url = arguments.epstein_files

    #Initialize datasets - TODO: Move this into the Dataset object when Clean and Raw datasets are implemented
    for set_index in range(Settings.dataset_count):
        #if(Settings.dataset_pages[set_index+1] > 10): Settings.dataset_pages[set_index+1] = 10    #TODO: Debug clamp
        datasets.append(Dataset(Settings.live_paginated_base_url, Settings.live_files_base_url, set_index+1))
    print(f"Initialized {len(datasets)} datasets")

    if(arguments.paginate):
        paginate()

    if(arguments.cleanup):
        cleanup()

    print("Program finished")

def paginate():
    process_name = "live_links_raw"

    logger = Log(Settings.local_output_files_url, process_name)
    logging_thread = threading.Thread(target=logger.append_logs_thread)
    logging_thread.start()

    pagination_handler = LivePaginationHandler(Settings.live_paginated_base_url)

    csv_writer = CsvWriter(logger, process_name, ['dataset_index', 'page_index', 'sequence_number', 'file_type', 'public_link'])
    csv_writer_thread = threading.Thread(target=csv_writer.append_csv_thread)
    csv_writer_thread.start()

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
        count_files += datasets[set_index].get_raw_file_count()
    logger.log(f"Pagination completed - {count_files} links in {count_pages} pages across {Settings.dataset_count} datasets")
    
    #TODO: Write csv directly from the dataset as pagination threads complete
    for set_index in range(Settings.dataset_count):
        for metadata in datasets[set_index].raw_file_metadata_list:
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

def cleanup():  #TODO: Look into pandas dataframes
    process_name = "live_links_clean"

    logger = Log(Settings.local_output_files_url, process_name)
    logging_thread = threading.Thread(target=logger.append_logs_thread)
    logging_thread.start()

    if(Path(f"{Settings.local_output_files_url}/live_links_raw.csv").is_file()):
        raw_csv_reader = CsvReader(logger, "live_links_raw")
    else:
        print("Raw links file not found, cannot proceed with cleanup. Check log files for more details.")
        logger.log(f"Raw links file was not found at {Settings.local_output_files_url}/live_links_raw.csv")
        logger.close()
        logging_thread.join()
        return
    
    if(Path(f"{Settings.local_output_files_url}/{process_name}.csv").is_file()):    #Ask if the user would like to overwrite it instead
        print("Clean links file already exists. Please move or delete it before running cleanup.")
        logger.log(f"Clean links file already exists at {Settings.local_output_files_url}/{process_name}.csv")
        logger.close()
        logging_thread.join()
        return
    
    clean_csv_writer = CsvWriter(logger, process_name, ['dataset_index', 'page_index', 'sequence_number', 'file_type', 'public_link'])
    clean_csv_writer_thread = threading.Thread(target=clean_csv_writer.append_csv_thread)
    clean_csv_writer_thread.start()

    print("Reading raw links file...")
    for dataset_index, file_metadata in raw_csv_reader.read_rows():
        datasets[dataset_index-1].raw_file_metadata_list.append(file_metadata)   #dataset_index is 1-based, list is 0-based
    raw_csv_reader.close()

    print("Sorting datasets...")
    for set_index in range(Settings.dataset_count): #Sort datasets
        dataset_metadata_list = datasets[set_index].raw_file_metadata_list[::]
        datasets[set_index].raw_file_metadata_list = sorted(dataset_metadata_list, key=lambda metadata:metadata.sequence)
        
    print("Beginning cleanup process...")
    for set_index in range(Settings.dataset_count):
        dataset = datasets[set_index]
        for metadata in dataset.raw_file_metadata_list: #Since these were just sorted, we should be able to add uniques directly to the csv in the correct sequence
            if(dataset.clean_file_metadata_list.get(metadata.sequence) is None):   #If we haven't seen this sequence number before, add it to the clean list
                dataset.clean_file_metadata_list[metadata.sequence] = metadata
                clean_csv_writer.rows_queue.put(metadata.get_row_data(dataset.dataset_index))
            else:   #Otherwise, we've seen this sequence number before, ignore the new one but log the duplicate
                logger.log(f"Dataset {set_index+1} sequence {metadata.sequence} duplicate ignored - Duplicate Page #{metadata.page_index} - Link: {metadata.public_link}")

    clean_csv_writer.close()
    print("Finished buffering clean links file. Waiting for writer thread to complete...")
    clean_csv_writer_thread.join()    #Wait for csv writing to complete
    
    logger.close()
    print("Finished buffering log file. Waiting for writer thread to complete...")
    logging_thread.join()


if __name__ == '__main__':
    main()