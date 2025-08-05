from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

from pydantic import field_validator
from sqlmodel import Field, Relationship, SQLModel


class VariableConfig(SQLModel):
    thr_min: float = -float("inf")
    thr_min_sel: Optional[float] = None
    thr_max: float = float("inf")
    thr_max_sel: Optional[float] = None
    selected: bool = False
    unit: str
    x_axis: bool = False
    y_axis: bool = False
    z_axis: bool = False


class ConfigProcessBase(VariableConfig):
    var_name: str
    downsampling: float = 1


class ConfigFileLink(SQLModel, table=True):
    config_id: Optional[int] = Field(
        default=None, foreign_key="configprocess.id", primary_key=True
    )
    file_id: Optional[int] = Field(
        default=None, foreign_key="file.id", primary_key=True
    )


class ConfigProcess(ConfigProcessBase, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    project_id: Optional[int] = Field(default=None, foreign_key="project.id")

    files: List["File"] = Relationship(
        back_populates="config_processes", link_model=ConfigFileLink
    )


class ConfigProcessCreate(ConfigProcessBase):
    pass


class VariableConfigRead(VariableConfig):
    files: Optional[List[str]] = []


class ConfigProcessRead(SQLModel):
    downsampling: float
    variables: Dict[str, VariableConfigRead]


# ----------------------------
# ----------------------------


class ProjectFileLink(SQLModel, table=True):
    project_id: Optional[int] = Field(
        default=None, foreign_key="project.id", primary_key=True
    )
    file_id: Optional[int] = Field(
        default=None, foreign_key="file.id", primary_key=True
    )


class File(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    path: str

    projects: List["Project"] = Relationship(
        back_populates="files", link_model=ProjectFileLink
    )
    config_processes: List[ConfigProcess] = Relationship(
        back_populates="files", link_model=ConfigFileLink
    )


class ProjectBase(SQLModel):
    name: str
    favourite: bool = False
    description: Optional[str] = None


class Project(ProjectBase, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    created: datetime = Field(default_factory=datetime.utcnow)
    last_opened: Optional[datetime] = None
    files: List[File] = Relationship(
        back_populates="projects", link_model=ProjectFileLink
    )


class ProjectCreate(ProjectBase):
    paths: List[str] = []

    @field_validator("paths")
    @classmethod
    def validate_file_paths(cls, v: List[str]) -> List[str]:
        if not v:
            return v

        from api.exceptions import InvalidFileExtensionError, MixedFileTypesError

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
    paths: List[str] = []
    config_process: ConfigProcessRead = None


class ProjectUpdate(ProjectBase):
    paths: List[str] = []
    config_process: ConfigProcessRead = None

    @field_validator("paths")
    @classmethod
    def validate_file_paths(cls, v: List[str]) -> List[str]:
        if not v:
            return v

        from api.exceptions import InvalidFileExtensionError, MixedFileTypesError

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
# ----------------------------


class ProcessJob(SQLModel, table=True):
    id: int = Field(default=None, primary_key=True)
    project_id: Optional[int] = Field(default=None, foreign_key="project.id")
    status: str = "pending"  # "pending", "processing", "done", "error"
    progress: float = 0.0
    result_path: Optional[str] = Field(default=None, nullable=True)
    error: Optional[str] = Field(default=None, nullable=True)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


# ----------------------------
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
