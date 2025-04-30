from fastapi import UploadFile

VALID_SUFFIX = ['pdf', 'doc', 'docx', 'jpg', 'jpeg', 'png', 'xls', 'xlsm', 'xlsx']
VALID_IMAGE_SUFFIX = ['jpg', 'jpeg', 'png']
MAX_FILE_SIZE = 100
VALID_CONTENT_TYPE = [
    'application/pdf',
    'application/msword',
    'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
    'image/jpeg',
    'image/png',
    'application/vnd.ms-excel',
    'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
]


def is_valid_file_type(file: UploadFile) -> bool:
    return file.content_type in VALID_CONTENT_TYPE
