from typing import List, Optional

from sqlmodel import SQLModel


class RenderBase(SQLModel):
    var_name: str

    thr_min: Optional[float] = None
    thr_min_sel: Optional[float] = None
    thr_max: Optional[float] = None
    thr_max_sel: Optional[float] = None
    scaling: Optional[str] = None

    mapping: Optional[str] = None
    colormap: Optional[str] = None
    opacity: Optional[float] = None
    invert_mapping: Optional[bool] = False


class RenderUpdate(RenderBase):
    variables: List[RenderBase] = []


class RenderRead(RenderBase):
    variables: List[RenderBase] = []
