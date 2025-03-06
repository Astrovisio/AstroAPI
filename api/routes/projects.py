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
from api.utils import read_data

router = APIRouter(prefix="/projects", tags=["projects"])


@router.get("/", response_model=List[ProjectRead])
def read_projects(*, session: SessionDep):
    return crud_project.get_projects(session)


@router.post("/", response_model=ProjectRead)
def create_new_project(*, session: SessionDep, project: ProjectCreate):
    project = crud_project.create_project(session, project)
    confs = read_data(project.files)
    confs_db = []
    for conf in confs:
        conf_db = crud_config_process.create_config_process(session, conf, project.id)
        confs_db.append(conf_db)
    conf_read = crud_config_process._build_config_process_read(confs_db)

    project_read = ProjectRead.model_validate(project)
    project_read.paths = [file.path for file in project.files]
    project_read.config_process = conf_read

    return project_read


@router.get("/{project_id}", response_model=ProjectRead)
def read_project(*, session: SessionDep, project_id: int):
    project = crud_project.get_project(session, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    return project


@router.put("/{project_id}", response_model=ProjectRead)
def update_project(*, session: SessionDep, project_id: int, project: ProjectUpdate):
    project_db = crud_project.update_project(session, project_id, project)
    new_confs_db = []
    conf_read = crud_config_process.get_config_process(session, project_id)
    if "paths" in project.dict(exclude_unset=True):
        confs = read_data(project_db.files)
        crud_config_process.delete_config_process(session, project_id)
        for conf in confs:
            conf_db = crud_config_process.create_config_process(
                session, conf, project_id
            )
            new_confs_db.append(conf_db)
        conf_read = crud_config_process._build_config_process_read(new_confs_db)

    project_read = ProjectRead.model_validate(project_db)
    project_read.paths = [file.path for file in project_db.files]
    project_read.config_process = conf_read
    return project_read


@router.delete("/{project_id}")
def remove_project(*, session: SessionDep, project_id: int):
    crud_project.delete_project(session, project_id)
    return {"message": "Project deleted successfully"}


@router.post("/{project_id}/process")
def process_data(*, session: SessionDep, project_id: int, config: ConfigProcess):
    config.project_id = project_id
    return crud_config_process.create_config_process(session, config)


@router.post("/{project_id}/render")
def create_render_config(*, session: SessionDep, project_id: int, config: ConfigRender):
    config.project_id = project_id
    return crud_config_render.create_render(session, config)
