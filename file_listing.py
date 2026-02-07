class FileDescriptor:

    def __init__(self, dataset_index, page_index, sequence_number, file_type, public_link):
        self.dataset_index = dataset_index
        self.page_index = page_index
        self.sequence = sequence_number
        self.type = file_type
        self.public_link = public_link

    @classmethod
    def from_row_data(cls, row_data:dict) -> FileDescriptor:
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