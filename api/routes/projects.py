from fastapi import APIRouter, HTTPException
from typing import List
from api.models import (
    ProjectCreate,
    ProjectUpdate,
    ProjectRead,
    ConfigProcess,
    ConfigRender,
)
from api.crud import crud_project, crud_config_process, crud_config_render
from api.db import SessionDep

router = APIRouter(prefix="/projects", tags=["projects"])


@router.get("/", response_model=List[ProjectRead])
def read_projects(*, session: SessionDep):
    return crud_project.get_projects(session)


@router.post("/", response_model=ProjectRead)
def create_new_project(*, session: SessionDep, project: ProjectCreate):
    return crud_project.create_project(session, project)


@router.get("/{project_id}", response_model=ProjectRead)
def read_project(*, session: SessionDep, project_id: int):
    project = crud_project.get_project(session, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    return project


@router.put("/{project_id}", response_model=ProjectRead)
def update_project(*, session: SessionDep, project_id: int, project: ProjectUpdate):
    project = crud_project.get_project(session, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    return crud_project.update_project(session, project, project)


@router.delete("/{project_id}")
def remove_project(*, session: SessionDep, project_id: int):
    project = crud_project.get_project(session, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    crud_project.delete_project(session, project)
    return {"message": "Project deleted"}


@router.post("/{project_id}/process")
def modify_process(*, session: SessionDep, project_id: int, config: ConfigProcess):
    config.project_id = project_id
    return crud_config_process.create_process(session, config)


@router.post("/{project_id}/render")
def modify_render(*, session: SessionDep, project_id: int, config: ConfigRender):
    config.project_id = project_id
    return crud_config_render.create_render(session, config)
