import logging

from fastapi import status

from api.exceptions import APIException

logger = logging.getLogger(__name__)


class ProjectNotFoundError(APIException):
    def __init__(self, project_id: int):
        super().__init__(
            status_code=status.HTTP_404_NOT_FOUND,
            error_code="PROJECT_NOT_FOUND",
            detail=f"Project with id {project_id} not found",
            context={"project_id": project_id},
        )


class FileNotFoundError(APIException):
    def __init__(self, file_id: int = None, file_path: str = None):
        if file_id:
            detail = f"File with id {file_id} not found"
            context = {"file_id": file_id}
        else:
            detail = f"File with path '{file_path}' not found"
            context = {"file_path": file_path}

        super().__init__(
            status_code=status.HTTP_404_NOT_FOUND,
            error_code="FILE_NOT_FOUND",
            detail=detail,
            context=context,
        )


class VariableNotFoundError(APIException):
    def __init__(
        self, variable_id: int = None, var_name: str = None, file_id: int = None
    ):
        if variable_id:
            detail = f"Variable with id {variable_id} not found"
            context = {"variable_id": variable_id}
        else:
            detail = f"Variable '{var_name}' not found in file {file_id}"
            context = {"var_name": var_name, "file_id": file_id}

        super().__init__(
            status_code=status.HTTP_404_NOT_FOUND,
            error_code="VARIABLE_NOT_FOUND",
            detail=detail,
            context=context,
        )


class FileProcessingError(APIException):
    def __init__(self, file_paths: list, error_details: str):
        super().__init__(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            error_code="FILE_PROCESSING_ERROR",
            detail=f"Failed to process files: {error_details}",
            context={"file_paths": file_paths, "error_details": error_details},
        )
