from typing import List

import msgpack
import logging
from fastapi import APIRouter, Response
import polars as pl

from api.crud import crud_config_process, crud_project, update_project_config
from api.db import SessionDep
from api.exceptions import DataProcessingError, ProjectNotFoundError
from api.models import ConfigProcessRead, ProjectCreate, ProjectRead, ProjectUpdate
from api.utils import data_processor

router = APIRouter(prefix="/projects", tags=["projects"])
logger = logging.getLogger(__name__)


@router.get("/", response_model=List[ProjectRead])
def read_projects(*, session: SessionDep):
    return crud_project.get_projects(session)


@router.post("/", response_model=ProjectRead)
def create_new_project(*, session: SessionDep, project: ProjectCreate):
    project = crud_project.create_project(session, project)
    confs = data_processor.read_data(project.files)
    for file, vars in confs.items():
        for var_name, conf in vars.items():
            conf_db = crud_config_process.create_config_process(session, conf, project.id)
            crud_config_process.associate_config_file(session, conf_db.id, file)
    conf_read = crud_config_process._build_config_process_read(session, project.id)

    project_read = ProjectRead.model_validate(project)
    project_read.paths = [file.path for file in project.files]
    project_read.config_process = conf_read

    return project_read


@router.get("/{project_id}", response_model=ProjectRead)
def read_project(*, session: SessionDep, project_id: int):
    project = crud_project.get_project(session, project_id)
    if not project:
        raise ProjectNotFoundError(project_id)
    return project


@router.put("/{project_id}", response_model=ProjectRead)
def update_project(*, session: SessionDep, project_id: int, project: ProjectUpdate):
    project_db = crud_project.update_project(session, project_id, project)
    conf_read = crud_config_process._build_config_process_read(session, project_id)

    project_read = ProjectRead.model_validate(project_db)
    project_read.paths = [file.path for file in project_db.files]
    project_read.config_process = conf_read
    return project_read


@router.delete("/{project_id}")
def remove_project(*, session: SessionDep, project_id: int):
    crud_project.delete_project(session, project_id)
    return {"message": "Project deleted successfully"}


@router.post("/{project_id}/process", response_class=Response)
def process(*, session: SessionDep, project_id: int, config: ConfigProcessRead):
    project = crud_project.get_project(session, project_id)
    if not project:
        raise ProjectNotFoundError(project_id)

    try:
        paths = project.paths
        update_project_config(session, project_id, config)
        processed_data: pl.DataFrame = data_processor.process_data(project_id, paths, config)
        logging.info(f"Processed data for project {project_id} with {len(processed_data)} rows.")
        binary_data = msgpack.packb(
            {
                "columns": processed_data.columns,
                "rows": processed_data.rows(),
            },
            use_bin_type=True,
        )
        return Response(content=binary_data, media_type="application/octet-stream")
    except Exception as e:
        raise DataProcessingError(str(e), {"project_id": project_id})


# @router.post("/{project_id}/render")
# def create_render_config(*, session: SessionDep, project_id: int, config: ConfigRender):
#     config.project_id = project_id
#     return crud_config_render.create_render(session, config)
