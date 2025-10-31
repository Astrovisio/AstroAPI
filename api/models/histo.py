from sqlmodel import SQLModel


class HistoBase(SQLModel):
    bin_index: int
    bin_min: float
    bin_max: float
    count: int
