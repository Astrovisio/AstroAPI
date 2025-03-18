from typing import Annotated, Generator

from fastapi import Depends, HTTPException
from sqlmodel import Session, SQLModel, create_engine

DATABASE_URL = "sqlite:///./prod.db"
engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})


def create_db_and_tables():
    SQLModel.metadata.create_all(engine)


def get_session() -> Generator[Session, None, None]:
    try:
        with Session(engine) as session:
            yield session
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal Server Error: {str(e)}")


SessionDep = Annotated[Session, Depends(get_session)]
