from typing import Optional

from sqlmodel import SQLModel


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


class VariableRead(VariableBase):
    pass


class VariableUpdate(VariableBase):
    pass
