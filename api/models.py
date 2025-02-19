from sqlmodel import SQLModel, Field, Relationship
from datetime import datetime
from typing import Optional, List


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


class ProjectRead(ProjectBase):
    id: int
    created: datetime
    last_opened: Optional[datetime]
    paths: List[str] = []


class ProjectUpdate(ProjectBase):
    paths: List[str] = []


# ----------------------------
# ----------------------------


class ConfigProcessBase(SQLModel):
    project_id: int
    var_name: str
    thr_min: float
    thr_max: float
    selected: bool
    downsampling: float
    x_axis: bool
    y_axis: bool
    z_axis: bool


class ConfigProcess(ConfigProcessBase, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)


class ConfigProcessCreate(ConfigProcessBase):
    pass


class ConfigProcessRead(ConfigProcessBase):
    id: int


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
