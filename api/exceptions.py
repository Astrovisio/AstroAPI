from typing import Any, Dict, List, Optional

from fastapi import HTTPException


class APIException(HTTPException):
    """Base API exception with enhanced error details"""

    def __init__(
        self,
        status_code: int,
        detail: str,
        error_code: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None,
    ):
        super().__init__(status_code=status_code, detail=detail)
        self.error_code = error_code
        self.context = context or {}


class ProjectNotFoundError(APIException):
    def __init__(self, project_id: int):
        super().__init__(
            status_code=404,
            detail=f"Project with id {project_id} not found",
            error_code="PROJECT_NOT_FOUND",
            context={"project_id": project_id},
        )


class ConfigProcessNotFoundError(APIException):
    def __init__(self, project_id: int, var_name: str):
        super().__init__(
            status_code=404,
            detail=f"ConfigProcess not found for project {project_id} and variable '{var_name}'",
            error_code="CONFIG_PROCESS_NOT_FOUND",
            context={"project_id": project_id, "var_name": var_name},
        )


class DataProcessingError(APIException):
    def __init__(self, detail: str, context: Optional[Dict[str, Any]] = None):
        super().__init__(
            status_code=422,
            detail=f"Data processing failed: {detail}",
            error_code="DATA_PROCESSING_ERROR",
            context=context or {},
        )


class InvalidFileExtensionError(APIException):
    def __init__(self, invalid_files: List[str], allowed_extensions: List[str]):
        super().__init__(
            status_code=422,
            detail=f"Invalid file extensions found. Only {', '.join(allowed_extensions)} files are allowed",
            error_code="INVALID_FILE_EXTENSION",
            context={
                "invalid_files": invalid_files,
                "allowed_extensions": allowed_extensions,
            },
        )


class MixedFileTypesError(APIException):
    def __init__(self, file_types: List[str]):
        super().__init__(
            status_code=422,
            detail="Cannot mix different file types in the same project",
            error_code="MIXED_FILE_TYPES",
            context={"file_types_found": file_types},
        )
