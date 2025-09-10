from typing import Optional

from sqlmodel import Field, SQLModel


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
