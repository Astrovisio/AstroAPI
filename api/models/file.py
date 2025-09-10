from typing import List, Optional

from sqlmodel import SQLModel

from .variable import VariableBase, VariableRead, VariableUpdate


class FileBase(SQLModel):
    file_type: str
    file_path: str
    processed: bool = False
    downsampling: float = 1.0
    processed_path: Optional[str] = None


class FileCreate(FileBase):
    variables: List[VariableBase] = []


class FileRead(FileBase):
    id: int
    variables: List[VariableRead] = []


class FileUpdate(FileBase):
    variables: List[VariableUpdate] = []
