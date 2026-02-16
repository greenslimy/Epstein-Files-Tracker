from concurrent.futures import ThreadPoolExecutor
from pymediainfo import MediaInfo
from pypdf import PdfReader
import pypdf.errors

from csv_file import CsvWriter
from file_listing import FileDescriptor
from files_logging import Log
from settings import Settings

class FileTabulator:

    def __init__(self, logger:Log, tabulated_local_files_csv_writer:CsvWriter, missing_local_files_csv_writer:CsvWriter):
        self.logger = logger
        self._pool = ThreadPoolExecutor(max_workers=12)
        self.tabulated_local_files_csv_writer = tabulated_local_files_csv_writer
        self.missing_local_files_csv_writer = missing_local_files_csv_writer

    def submit_file(self, file_descriptor:FileDescriptor):
        return self._pool.submit(self._tabulate_file_thread, file_descriptor)

    def _tabulate_file_thread(self, file_descriptor:FileDescriptor):
        full_file_name = f"EFTA{file_descriptor.sequence:08d}.{file_descriptor.type}"
        file_path = f"{Settings.local_files_base_url}/DataSet {file_descriptor.dataset_index}/{full_file_name}"
        sequence_number = file_descriptor.sequence

        if(file_descriptor.does_local_file_exist()):
            file_name = file_path.split("/")[-1]
            file_type = file_name.split(".")[-1].lower()

            try:
                num_bytes, length, unit_of_measure = get_file_info(file_path, file_type)
                if num_bytes == 0:
                    self.missing_local_files_csv_writer.rows_queue.put({
                        'dataset_index': file_descriptor.dataset_index,
                        'sequence_number': sequence_number,
                        'file_name': file_name,
                        'local_file_path': file_path,
                        'public_link': file_descriptor.public_link
                    })
                else:
                    self.tabulated_local_files_csv_writer.rows_queue.put({
                        'dataset_index': file_descriptor.dataset_index,
                        'sequence_number': sequence_number,
                        'file_name': file_name,
                        'num_bytes': num_bytes,
                        'length': length,
                        'unit_of_measure': unit_of_measure
                    })

                    return True
            except Exception as e:
                self.logger.log(f"Error tabulating file {file_path}: {e}")
                self.missing_local_files_csv_writer.rows_queue.put({
                    'dataset_index': file_descriptor.dataset_index,
                    'sequence_number': sequence_number,
                    'file_name': file_name,
                    'local_file_path': file_path,
                    'public_link': file_descriptor.public_link
                })
        else:
            self.logger.log(f"Local file missing: {full_file_name}")
            self.missing_local_files_csv_writer.rows_queue.put({
                'dataset_index': file_descriptor.dataset_index,
                'sequence_number': file_descriptor.sequence,
                'file_name': full_file_name, 
                'local_file_path': file_path, 
                'public_link': file_descriptor.public_link
            })

        return False

def get_file_info(file_path:str, file_type:str) -> tuple[int, int, str]:
    """
    Inspects local file to get number of bytes and either duration (for video files) or page count (for PDFs). If the file type is not recognized, it will return the number of bytes and -1 for length with "unknown" as the unit of measure.
    
    :param file_path: Path to the file to analyze
    :type file_path: str
    :param file_type: Type of the file (e.g., 'mp4', 'avi', 'xlsx', 'pdf')
    :type file_type: str
    :return: bytes, length, unit_of_measure
    :rtype: tuple[int, int, str]
    """
    local_epstein_file = open(file_path, "rb")
    num_bytes = local_epstein_file.seek(0, 2)   #Seek to end of file to get number of bytes
    local_epstein_file.close()  #Close it so it can be reopened by other functions, e.g. get_pdf_page_count

    if file_type in ['mp4', 'avi', 'mkv', 'mov']:
        duration_ms = get_video_file_duration(file_path)
        return (num_bytes, duration_ms, "ms")
    elif file_type == 'pdf':
        page_count = get_pdf_page_count(file_path)
        return (num_bytes, page_count, "pages")
    else:
        return (num_bytes, -1, "unknown")

def get_video_file_duration(file_path) -> int:
    try:
        media_info = MediaInfo.parse(file_path)
        for track in media_info.tracks:
            if track.track_type == "General":
                return track.duration
    except Exception as e:
        print(f"Error reading video file: {e}")
    return 0

def get_pdf_page_count(file_path:str) -> int:
    try:
        with open(file_path, 'rb') as file:
            reader = PdfReader(file)
            return len(reader.pages)
    except (pypdf.errors.PdfStreamError, pypdf.errors.EmptyFileError) as e: #Some PDFs are not found (404) or are 0 bytes. E.g. https://www.justice.gov/epstein/files/DataSet%209/EFTA00067093.pdf
        print(f"Invalid PDF: {e}")
        return 0
    except Exception as e:
        print(f"Error reading PDF: {e}")

    return -1