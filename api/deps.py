from typing import Annotated, Generator

from fastapi import Depends, HTTPException
from sqlmodel import Session

from api.db import engine
from api.services import FileService, ProcessJobService, ProjectService


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


def file_service_dep(session: SessionDep) -> FileService:
    return FileService(session)


FileServiceDep = Annotated[FileService, Depends(file_service_dep)]


def processjob_service_dep(session: SessionDep):
    return ProcessJobService(session)


ProcessJobServiceDep = Annotated[ProcessJobService, Depends(processjob_service_dep)]
