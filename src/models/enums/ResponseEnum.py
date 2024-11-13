from enum import Enum

class ResponseSignal(Enum):
    FILE_VALIDATED_SUCCESS = "file_validate_successfully"
    FILE_TYPE_NOT_SUPPORTED = "file_type_not_supported"
    FILE_SIZE_EXCEEDED = "file_size_excedded"
    FILE_UPLOAD_FAILED = "file_upload_failed"
    FILE_UPLOAD_SUCCESS = "file_upload_success"
    PROCESSING_FAILED = "process_failed"
    PROCESSING_SUCCEDED = "process_succeded"