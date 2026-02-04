import threading
from dataset import Dataset
import watchdog
from files_logging import Log
import csv
from web import LivePaginationHandler
import argparse
from settings import Settings

datasets:list[Dataset] = []

def main():
    argument_parser = argparse.ArgumentParser()
    argument_parser.add_argument('-o', dest="local_output", type=str, help="Local location you would like output files to be written. Be sure to create a logs directory first!", required=True)
    argument_parser.add_argument('-f', dest="local_files", type=str, help="Local location of your copy of the unzipped files")
    argument_parser.add_argument('--paginate', action="store_true", help="Paginate and record links from the justice.gov live release of the files")
    arguments = argument_parser.parse_args()

    Settings.local_output_files_url = arguments.local_output
    Settings.local_files_base_url = arguments.local_files

    #Initialize datasets
    for set_index in range(Settings.dataset_count):
        #if(Settings.dataset_pages[set_index+1] > 50): Settings.dataset_pages[set_index+1] = 50    #TODO: Debug clamp
        datasets.append(Dataset(Settings.live_paginated_base_url, Settings.live_files_base_url, set_index+1))
    print(f"Initialized {len(datasets)} datasets")

    if(arguments.paginate):
        paginate()

    print("Program finished")

def paginate():
    logger = Log(Settings.local_output_files_url, "gather_live_links")
    logging_thread = threading.Thread(target=logger.append_logs)
    logging_thread.start()

    pagination_handler = LivePaginationHandler(Settings.live_paginated_base_url)

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

    #  Sort and output the list of publically listed files to a csv  #
    all_files_metadata = []
    print("Sorting all dataset files...")
    for set_index in range(Settings.dataset_count):
        dataset_metadata_list = datasets[set_index].file_metadata_list[::]
        datasets[set_index].file_metadata_list = sorted(dataset_metadata_list, key=lambda metadata:metadata.sequence)
    
    for set_index in range(Settings.dataset_count):
        for metadata in datasets[set_index].file_metadata_list:
            all_files_metadata.append({
                'dataset_index': set_index+1,
                'page_index': metadata.page_index,
                'sequence_number': metadata.sequence,
                'file_type': metadata.type,
                'public_link': metadata.public_link
            })

    local_live_links_csv_path = f"{Settings.local_output_files_url}/live_links_duplicates.csv"
    print(f"\nWriting details to {local_live_links_csv_path}")
    with open(local_live_links_csv_path, 'x', newline='') as csvfile:
        headers = ['dataset_index', 'page_index', 'sequence_number', 'file_type', 'public_link']
        writer = csv.DictWriter(csvfile, fieldnames=headers)
        writer.writeheader()
        writer.writerows(all_files_metadata)
        logger.log(f"Wrote detail file to {local_live_links_csv_path}")
        csvfile.close()
    print("Finished writing live links file. Waiting for logging thread to complete...")
    logger.log("REMINDER: This file will likely contain many duplicates. This is how they were presented on the live justice.gov website.")

    logger.program_completed = True
    logging_thread.join()
    print("REMINDER: This file will likely contain many duplicates. This is how they were presented on the live justice.gov website.")

if __name__ == '__main__':
    main()