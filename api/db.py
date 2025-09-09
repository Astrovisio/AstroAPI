import os
from typing import Annotated, Generator

from fastapi import Depends, HTTPException
from sqlalchemy.orm import sessionmaker
from sqlmodel import Session, SQLModel, create_engine

from api.services import ProjectService

# Ensure data directory exists
os.makedirs("./data/astrovisio_files", exist_ok=True)

DATABASE_URL = "sqlite:///./data/astrovisio_files/prod.db"

engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(
    class_=Session, autocommit=False, autoflush=False, bind=engine
)


def create_db_and_tables():
    SQLModel.metadata.create_all(engine)


def get_session() -> Generator[Session, None, None]:
    try:
        with Session(engine) as session:
            yield session
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal Server Error: {str(e)}")


SessionDep = Annotated[Session, Depends(get_session)]


def project_service_dep(session: SessionDep) -> ProjectService:
    return ProjectService(session)


ProjectServiceDep = Annotated[ProjectService, Depends(project_service_dep)]
