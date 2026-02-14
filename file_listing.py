from abc import abstractmethod
from pathlib import Path
from settings import Settings

class CsvEntry:
    
    @classmethod
    def from_row_data(cls, row_data:dict[str, str]) -> CsvEntry:
        raise NotImplementedError("Subclasses must implement from_row_data method")

class FileDescriptor(CsvEntry):

    def __init__(self, dataset_index, page_index, sequence_number, file_type, public_link):
        self.dataset_index = dataset_index
        self.page_index = page_index
        self.sequence = sequence_number
        self.type = file_type
        self.public_link = public_link

    @classmethod
    def from_row_data(cls, row_data:dict[str, str]) -> FileDescriptor:
        return (cls(
            int(row_data['dataset_index']),
            int(row_data['page_index']),
            int(row_data['sequence_number']),
            row_data['file_type'],
            row_data['public_link']
        ))
    
    def get_row_data(self) -> dict:
        return {
            'dataset_index': self.dataset_index,
            'page_index': self.page_index,
            'sequence_number': self.sequence,
            'file_type': self.type,
            'public_link': self.public_link
        }
    
    def does_local_file_exist(self) -> bool:
        local_file_path = f"{Settings.local_files_base_url}/DataSet {self.dataset_index}/EFTA{self.sequence:08d}.{self.type}"
        return Path(local_file_path).is_file()
    
class EpsteinFile(CsvEntry):

    def __init__(self, sequence:int, file_name:str, num_bytes:int, length:float, unit_of_measure:str):
        self.sequence = sequence
        self.file_name = file_name
        self.num_bytes = num_bytes
        self.length = length
        self.unit_of_measure = unit_of_measure

    @classmethod
    def from_row_data(cls, row_data:dict) -> EpsteinFile:
        return (cls(
            int(row_data['sequence_number']),
            row_data['file_name'],
            int(row_data['num_bytes']),
            float(row_data['length']),
            row_data['unit_of_measure']
        ))
        

    def get_row_data(self) -> dict:
        return {
            'sequence_number': self.sequence,
            'file_name': self.file_name,
            'num_bytes': self.num_bytes,
            'length': self.length,
            'unit_of_measure': self.unit_of_measure
        }
    
class MissingFile(CsvEntry):

    def __init__(self, sequence:int, file_name:str, local_file_path:str, public_link:str):
        self.sequence = sequence
        self.file_name = file_name
        self.local_file_path = local_file_path
        self.public_link = public_link

    @classmethod
    def from_row_data(cls, row_data:dict) -> MissingFile:
        return (cls(
            int(row_data['sequence_number']),
            row_data['file_name'],
            row_data['local_file_path'],
            row_data['public_link'])
        )
        

    def get_row_data(self) -> dict:
        return {
            'sequence_number': self.sequence,
            'file_name': self.file_name,
            'local_file_path': self.local_file_path,
            'public_link': self.public_link
        }