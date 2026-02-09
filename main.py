import threading
from csv_file import CsvWriter, CsvReader
from dataset import Dataset
from file_listing import EpsteinFile, FileDescriptor
from file_tabulate import get_file_info
import watchdog
from files_logging import Log
from web import WebRequestHandler, PaginationParsingHandler
import argparse
from settings import Settings
from pathlib import Path

datasets:list[Dataset] = []

def main():
    argument_parser = argparse.ArgumentParser(formatter_class=argparse.RawTextHelpFormatter, description="Epstein Files Tracker")
    argument_parser.add_argument('-o', dest="tracker_output", type=str, help="Local location you would like output files to be written. Be sure to create a logs directory first!\nTracker will look here for input .csv files that were created by this program.", required=True)
    argument_parser.add_argument('-f', dest="epstein_files", type=str, help="Local location of your copy of the unzipped Epstein Files")
    argument_parser.add_argument('--paginate', action="store_true", help="Paginate and record links from the justice.gov live release of the files")
    argument_parser.add_argument('--clean', action="store_true", help="Clean up duplicates and sort links from a previously generated live_links_raw.csv file")
    argument_parser.add_argument('--tabulate', action="store_true", help="Tabulate local files to get file statistics like byte size and length. Requires the -f path to be set.")
    arguments = argument_parser.parse_args()

    Settings.local_output_files_url = arguments.tracker_output
    Settings.local_files_base_url = arguments.epstein_files

    #Initialize datasets
    for set_index in range(Settings.dataset_count):
        #if(Settings.dataset_pages[set_index+1] > 10): Settings.dataset_pages[set_index+1] = 10    #TODO: Debug clamp
        datasets.append(Dataset(set_index+1))
    print(f"Initialized {len(datasets)} datasets")

    if(arguments.paginate):
        paginate()

    if(arguments.clean):
        cleanup()

    if(arguments.tabulate):
        if(Settings.local_files_base_url is None):
            print("Local files base URL not set. Please provide the location of your local copy of the Epstein Files with the -f argument before running the tabulate option.")
        else:
            tabulate_local_files()

    print("Program finished")

def paginate():
    process_name = "live_links_raw"

    logger = Log(process_name)
    logging_thread = threading.Thread(target=logger.append_logs_thread)
    logging_thread.start()

    successful_csv_writer = CsvWriter(logger, process_name, ['dataset_index', 'page_index', 'sequence_number', 'file_type', 'public_link'])
    successful_csv_writer_thread = threading.Thread(target=successful_csv_writer.append_csv_thread)
    successful_csv_writer_thread.start()

    failed_csv_writer = CsvWriter(logger, f"{process_name}_failed", ['dataset_index', 'page_index', 'http_status_code'])
    failed_csv_writer_thread = threading.Thread(target=failed_csv_writer.append_csv_thread)
    failed_csv_writer_thread.start()

    pagination_parsing_handler = PaginationParsingHandler(logger)

    pagination_url_handler = WebRequestHandler(logger, pagination_parsing_handler, failed_csv_writer)
    pagination_url_handler_thread = threading.Thread(target=pagination_url_handler.error_watcher)   #Watches for rate limiting and pauses pagination when it occurs
    pagination_url_handler_thread.start()

    pagination_watchdog = watchdog.Pagination(logger, pagination_url_handler, datasets)
    pagination_watchdog_thread = threading.Thread(target=pagination_watchdog.update)   #Keeps track of each dataset thread's progress and updates the console
    pagination_watchdog_thread.start()

    for dataset in datasets:
        dataset.set_logger(logger)   #Set the logger for each dataset so they can log their pagination progress
        dataset.paginate(pagination_url_handler, successful_csv_writer)   #Start paginating each dataset. This will submit all the page URLs to the pagination handler, which will handle the multithreading and parsing of each page. The dataset threads will then wait for the pagination watchdog to confirm that all pages have been parsed before they finish.

    pagination_watchdog_thread.join()   #Wait for the watchdog to confirm all datasets have been paginated before continuing

    logger.log(f"Pagination completed for all datasets. Check {successful_csv_writer.csv_file.name} for the list of links and {failed_csv_writer.csv_file.name} for any failed page requests.")

    successful_csv_writer.close()
    failed_csv_writer.close()
    print("Finished buffering live links file. Waiting for writer thread to complete...")
    successful_csv_writer_thread.join()    #Wait for csv writing to complete
    failed_csv_writer_thread.join()        #Wait for csv writing to complete
    
    logger.log("REMINDER: This file will likely contain many duplicates. This is how they were presented on the live justice.gov website.")

    logger.close()
    print("Finished buffering log file. Waiting for writer thread to complete...")
    logging_thread.join()

    print("\nREMINDER: This file will likely contain many duplicates. This is how they were presented on the live justice.gov website.")

def cleanup():  #TODO: Look into pandas dataframes
    process_name = "live_links_clean"

    logger = Log(process_name)
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

    cleaned_metadata:dict[int, FileDescriptor] = {}   #Keyed by sequence number. We will assume that if there are duplicates, the one with the lowest page number is the correct one and ignore the rest.

    print("Reading raw links file...")
    for file_metadata in raw_csv_reader.read_all_rows():
        existing_entry = cleaned_metadata.get(file_metadata.sequence)
        if(existing_entry is None or file_metadata.type != "pdf"):   #If we haven't seen this sequence number before, add it to the clean list. If the existing file is a pdf, but the new one isn't, overwrite that entry. I.e. videos and other file types should take priority
            cleaned_metadata[file_metadata.sequence] = file_metadata
    raw_csv_reader.close()
    
    logger.log(f"Read {len(cleaned_metadata)} unique links from raw links file. Writing to clean links file and logging any duplicates found.")

    print("Sorting and writing clean links file...")
    cleaned_metadata = dict(sorted(cleaned_metadata.items()))

    for _, file_metadata in cleaned_metadata.items():
        if(file_metadata is not None):
            clean_csv_writer.rows_queue.put(file_metadata.get_row_data())

    print(f"Finished cleaning links file with {len(cleaned_metadata)} unique links.")

    clean_csv_writer.close()
    print("Finished buffering clean links file. Waiting for writer thread to complete...")
    clean_csv_writer_thread.join()    #Wait for csv writing to complete
    
    logger.close()
    print("Finished buffering log file. Waiting for writer thread to complete...")
    logging_thread.join()

def tabulate_local_files():
    process_name = "tabulate_local_files"

    logger = Log(process_name)
    logging_thread = threading.Thread(target=logger.append_logs_thread)
    logging_thread.start()

    clean_csv_reader = CsvReader(logger, "live_links_clean")

    tabulated_local_files_csv_writer = CsvWriter(logger, process_name, ['sequence_number', 'file_name', 'num_bytes', 'length', 'unit_of_measure'])
    tabulated_local_files_csv_writer_thread = threading.Thread(target=tabulated_local_files_csv_writer.append_csv_thread)
    tabulated_local_files_csv_writer_thread.start()

    missing_local_files_csv_writer = CsvWriter(logger, f"{process_name}_missing", ['sequence_number', 'file_name', 'local_file_path', 'public_link'])
    missing_local_files_csv_writer_thread = threading.Thread(target=missing_local_files_csv_writer.append_csv_thread)
    missing_local_files_csv_writer_thread.start()

    print("Tabulating local files from cleaned links file. Files will be processed in chunks of 1000 files.")
    chunk_index = 0
    for file_metadata in clean_csv_reader.read_rows_chunked(chunk_size=1000):   #Read in chunks to reduce disk usage
        chunk_index += 1
        logger.log(f"Tabulating chunk {chunk_index} with 1000 files...")
        for metadata in file_metadata:
            full_file_name = f"EFTA{metadata.sequence:08d}.{metadata.type}"
            if(metadata.does_local_file_exist()):
                local_epstein_file_path = f"{Settings.local_files_base_url}/DataSet {metadata.dataset_index}/{full_file_name}"
                file_statistics = get_file_info(local_epstein_file_path, metadata.type)
                epstein_file = EpsteinFile(metadata.sequence, full_file_name, file_statistics[0], file_statistics[1], file_statistics[2])
                tabulated_local_files_csv_writer.rows_queue.put(epstein_file.get_row_data())
            else:
                logger.log(f"Local file missing: {full_file_name}")
                missing_local_files_csv_writer.rows_queue.put({
                    'sequence_number': metadata.sequence,
                    'file_name': full_file_name, 
                    'local_file_path': f"{Settings.local_files_base_url}/DataSet {metadata.dataset_index}/{full_file_name}", 
                    'public_link': metadata.public_link
                })

    print("Finished tabulating local files. See log file for details.")
    clean_csv_reader.close()
    
    tabulated_local_files_csv_writer.close()
    missing_local_files_csv_writer.close()
    print("Finished buffering tabulated local files. Waiting for writer threads to complete...")
    tabulated_local_files_csv_writer_thread.join()    #Wait for csv writing to complete
    missing_local_files_csv_writer_thread.join()      #Wait for csv writing to complete

    logger.close()
    print("Finished buffering log file. Waiting for writer thread to complete...")
    logging_thread.join()


if __name__ == '__main__':
    main()