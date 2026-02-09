from pymediainfo import MediaInfo
from pypdf import PdfReader

def get_file_info(file_path:str, file_type:str) -> tuple[int, int, str]:
    """
    Docstring for get_file_info
    
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
    media_info = MediaInfo.parse(file_path)
    for track in media_info.tracks:
        if track.track_type == "General":
            return track.duration
    return 0

def get_pdf_page_count(file_path:str) -> int:
    with open(file_path, 'rb') as file:
        reader = PdfReader(file)
        return len(reader.pages)