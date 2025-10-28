from typing import List, Optional

from pydantic import field_validator
from sqlmodel import SQLModel


class RenderBase(SQLModel):
    var_name: Optional[str] = None

    vis_thr_min: Optional[float] = None
    vis_thr_min_sel: Optional[float] = None
    vis_thr_max: Optional[float] = None
    vis_thr_max_sel: Optional[float] = None
    scaling: Optional[str] = None

    mapping: Optional[str] = None
    colormap: Optional[str] = None
    opacity: Optional[float] = None
    invert_mapping: Optional[bool] = False


class RenderUpdate(SQLModel):
    variables: List[RenderBase] = []
    noise: Optional[float] = 0

    @field_validator("variables")
    @classmethod
    def validate_variables(cls, v: list) -> list:
        mappings = [var.mapping for var in v if var.mapping]
        if len(mappings) != len(set(mappings)):
            raise ValueError("Duplicate mapping values found in variables.")
        return v


class RenderRead(SQLModel):
    variables: List[RenderBase] = []
    noise: Optional[float] = 0
