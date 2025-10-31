from typing import List, Optional

from pydantic import field_validator
from sqlmodel import SQLModel

from .variable import VariableBase, VariableRead, VariableUpdate


class FileBase(SQLModel):
    type: str
    name: str
    path: str
    size: Optional[int] = None
    total_points: Optional[int] = None


class FileCreate(FileBase):
    variables: List[VariableBase] = []


class FileRead(FileBase):
    id: int
    processed: Optional[bool] = False
    downsampling: Optional[float] = 1.0
    processed_path: Optional[str] = None
    order: Optional[int] = -1
    variables: List[VariableRead] = []


class FileUpdate(FileBase):
    processed: Optional[bool] = False
    downsampling: Optional[float] = 1.0
    processed_path: Optional[str] = None
    variables: List[VariableUpdate] = []
    order: Optional[int] = -1

    @field_validator("downsampling")
    @classmethod
    def validate_downsampling(cls, v: float) -> float:
        if not (0 < v <= 1):
            raise ValueError(
                "downsampling must be between 0 (exclusive) and 1 (inclusive)"
            )
        return v
