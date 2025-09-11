from datetime import datetime
from typing import List, Optional

from sqlmodel import Field, Relationship, SQLModel

from .file import FileBase
from .project import ProjectBase


class FileProjectLink(SQLModel, table=True):
    project_id: Optional[int] = Field(
        default=None, foreign_key="project.id", primary_key=True
    )
    file_id: Optional[int] = Field(
        default=None, foreign_key="file.id", primary_key=True
    )


class Variable(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    file_id: int = Field(foreign_key="file.id")
    var_name: str
    unit: str
    thr_min: float = -float("inf")
    thr_max: float = float("inf")

    # Relationship
    file: "File" = Relationship(back_populates="variables")


class ProjectFileVariableConfig(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    project_id: int = Field(foreign_key="project.id")
    file_id: int = Field(foreign_key="file.id")
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


class ProcessJob(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    project_id: Optional[int] = Field(default=None, foreign_key="project.id")
    file_id: Optional[int] = Field(default=None, foreign_key="file.id")
    status: str = "pending"  # "pending", "processing", "done", "error"
    progress: float = 0.0
    result_path: Optional[str] = Field(default=None, nullable=True)
    error: Optional[str] = Field(default=None, nullable=True)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
