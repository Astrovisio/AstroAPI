from datetime import datetime
from pathlib import Path
from typing import List, Optional

from pydantic import field_validator
from sqlmodel import SQLModel

from api.exceptions import InvalidFileExtensionError, MixedFileTypesError

from .file import FileRead


class ProjectBase(SQLModel):
    name: str
    favourite: bool = False
    description: Optional[str] = None


class ProjectCreate(ProjectBase):
    paths: List[str] = []

    @field_validator("paths")
    @classmethod
    def validate_file_paths(cls, v: List[str]) -> List[str]:
        if not v:
            return v

        allowed_extensions = {".hdf5", ".fits"}
        file_extensions = set()
        invalid_files = []

        for path in v:
            ext = Path(path).suffix.lower()
            if ext not in allowed_extensions:
                invalid_files.append(path)
            else:
                file_extensions.add(ext)

        if invalid_files:
            raise InvalidFileExtensionError(invalid_files, list(allowed_extensions))

        if len(file_extensions) > 1:
            raise MixedFileTypesError(list(file_extensions))

        return v


class ProjectRead(ProjectBase):
    id: int
    created: datetime
    last_opened: Optional[datetime]
    files: List[FileRead] = []


class ProjectUpdate(ProjectBase):
    pass


class ProjectFilesUpdate(SQLModel):
    """Replace all files in a project"""

    paths: List[str]

    @field_validator("paths")
    @classmethod
    def validate_file_paths(cls, v: List[str]) -> List[str]:
        if not v:
            return v

        allowed_extensions = {".hdf5", ".fits"}
        file_extensions = set()
        invalid_files = []

        for path in v:
            ext = Path(path).suffix.lower()
            if ext not in allowed_extensions:
                invalid_files.append(path)
            else:
                file_extensions.add(ext)

        if invalid_files:
            raise InvalidFileExtensionError(invalid_files, list(allowed_extensions))

        if len(file_extensions) > 1:
            raise MixedFileTypesError(list(file_extensions))

        return v


class ProjectDuplicate(SQLModel):
    name: str
    description: str
