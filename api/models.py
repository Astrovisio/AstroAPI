from datetime import datetime
from pathlib import Path
from typing import List, Optional

from pydantic import field_validator
from sqlmodel import Field, Relationship, SQLModel

from api.exceptions import InvalidFileExtensionError, MixedFileTypesError

# ----------------------------
# Base Models
# ----------------------------


class ProjectBase(SQLModel):
    name: str
    favourite: bool = False
    description: Optional[str] = None


class FileBase(SQLModel):
    file_type: str
    file_path: str
    processed: bool = False
    downsampling: float = 1.0
    processed_path: Optional[str] = None


class VariableBase(SQLModel):
    var_name: str
    thr_min: float = -float("inf")
    thr_max: float = float("inf")
    thr_min_sel: Optional[float] = None
    thr_max_sel: Optional[float] = None
    selected: bool = False
    unit: str
    x_axis: bool = False
    y_axis: bool = False
    z_axis: bool = False


# ----------------------------
# Create  Models
# ----------------------------


class FileCreate(FileBase):
    variables: List[VariableBase] = []


class ProjectCreate(ProjectBase):
    file_paths: List[str] = []

    @field_validator("file_paths")
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


# ----------------------------
# Read Models
# ----------------------------


class VariableRead(VariableBase):
    pass


class FileRead(FileBase):
    variables: List[VariableRead] = []


class ProjectRead(ProjectBase):
    id: int
    created: datetime
    last_opened: Optional[datetime]
    files: List[FileRead] = []


# ----------------------------
# Update Models
# ----------------------------


class VariableUpdate(VariableBase):
    pass


class FileUpdate(FileBase):
    variables: List[VariableUpdate] = []


class ProjectUpdate(ProjectBase):
    """Update project metadata and variable configurations only"""

    files: List[FileUpdate] = []


class ProjectFilesUpdate(SQLModel):
    """Replace all files in a project"""

    file_paths: List[str]

    @field_validator("file_paths")
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


class FileProjectLink(SQLModel, table=True):
    project_id: Optional[int] = Field(
        default=None, foreign_key="project.id", primary_key=True
    )
    file_id: Optional[int] = Field(
        default=None, foreign_key="file.id", primary_key=True
    )


# ----------------------------
# Db Models
# ----------------------------


class Variable(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    file_id: int = Field(foreign_key="file.id")
    var_name: str
    unit: str
    thr_min: float = -float("inf")
    thr_max: float = float("inf")

    # Relationship
    file: "File" = Relationship(back_populates="variables")


class ProjectVariableConfig(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    project_id: int = Field(foreign_key="project.id")
    variable_id: int = Field(foreign_key="variable.id")
    thr_min_sel: Optional[float] = None
    thr_max_sel: Optional[float] = None
    selected: bool = False
    x_axis: bool = False
    y_axis: bool = False
    z_axis: bool = False


class File(FileBase, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    file_path: str = Field(index=True, unique=True)

    # Relationships
    projects: List["Project"] = Relationship(
        back_populates="files", link_model=FileProjectLink
    )
    variables: List[Variable] = Relationship(back_populates="file", cascade_delete=True)


class Project(ProjectBase, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    created: datetime = Field(default_factory=datetime.utcnow)
    last_opened: Optional[datetime] = None

    # Relationship
    files: List["File"] = Relationship(
        back_populates="projects", link_model=FileProjectLink
    )


# ----------------------------
# Process Job Models
# ----------------------------


class ProcessJob(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    project_id: Optional[int] = Field(default=None, foreign_key="project.id")
    status: str = "pending"  # "pending", "processing", "done", "error"
    progress: float = 0.0
    result_path: Optional[str] = Field(default=None, nullable=True)
    error: Optional[str] = Field(default=None, nullable=True)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


# ----------------------------
# Render Configuration Models
# ----------------------------


class ConfigRenderBase(SQLModel):
    project_id: int
    var_name: str
    colormap: str = "Inferno"
    contrast: float = 1.0
    saturation: float = 1.0
    opacity: float = 1.0
    brightness: float = 1.0
    shape: str = "square"
    thr_min: Optional[float] = None
    thr_max: Optional[float] = None


class ConfigRender(ConfigRenderBase, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)


class ConfigRenderCreate(ConfigRenderBase):
    pass


class ConfigRenderRead(ConfigRenderBase):
    id: int
