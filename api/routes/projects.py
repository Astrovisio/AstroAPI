import os
from threading import Thread
from typing import List

import msgpack
from fastapi import APIRouter, Response

from api.crud import (
    crud_config_process,
    crud_process_job,
    crud_project,
    update_project_config,
)
from api.db import SessionDep, SessionLocal
from api.exceptions import DataProcessingError, ProjectNotFoundError
from api.models import ConfigProcessRead, ProjectCreate, ProjectRead, ProjectUpdate
from api.utils import data_processor

router = APIRouter(prefix="/projects", tags=["projects"])


@router.get("/", response_model=List[ProjectRead])
def read_projects(*, session: SessionDep):
    return crud_project.get_projects(session)


@router.post("/", response_model=ProjectRead)
def create_new_project(*, session: SessionDep, project: ProjectCreate):
    project = crud_project.create_project(session, project)
    confs = data_processor.read_data(project.files)
    for file, vars in confs.items():
        for var_name, conf in vars.items():
            conf_db = crud_config_process.create_config_process(
                session, conf, project.id
            )
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


@router.post("/{project_id}/process")
def process(*, session: SessionDep, project_id: int, config: ConfigProcessRead):
    project = crud_project.get_project(session, project_id)
    if not project:
        raise ProjectNotFoundError(project_id)

    job = crud_process_job.create_process_job(session, project_id)

    def run_processing(job_id, session_maker, project, config):
        session = session_maker()
        try:

            def progress_callback(progress):
                progress = round(progress, 2)
                crud_process_job.update_process_job(session, job_id, progress=progress)

            crud_process_job.update_process_job(
                session, job_id, status="processing", progress=0.1
            )
            paths = project.paths
            update_project_config(session, project_id, config)
            processed_data = data_processor.process_data(
                project_id, paths, config, progress_callback=progress_callback
            )
            result_path = f"./data/project_{project.id}_processed.msgpack"
            data_dict = {
                "columns": processed_data.columns.tolist(),
                "rows": processed_data.values.tolist(),
            }
            binary_data = msgpack.packb(data_dict, use_bin_type=True)
            with open(result_path, "wb") as f:
                f.write(binary_data)
            crud_process_job.update_process_job(
                session, job_id, status="done", progress=1.0, result_path=result_path
            )
        except Exception as e:
            crud_process_job.update_process_job(
                session, job_id, status="error", error=str(e), progress=1.0
            )
        finally:
            session.close()

    Thread(target=run_processing, args=(job.id, SessionLocal, project, config)).start()

    return {"job_id": job.id}


@router.get("/{project_id}/process/{job_id}/progress")
def process_progress(*, session: SessionDep, project_id: int, job_id: int):
    job = crud_process_job.get_process_job(session, job_id)
    if not job:
        return {"error": "Job not found"}
    return {
        "status": job.status,
        "progress": job.progress,
        "error": job.error,
    }


@router.get("/{project_id}/process/{job_id}/result", response_class=Response)
def process_result(*, session: SessionDep, project_id: int, job_id: int):
    job = crud_process_job.get_process_job(session, job_id)
    if not job or job.status != "done" or not job.result_path:
        return Response(
            content="Job not found or not completed",
            status_code=404,
            media_type="text/plain",
        )
    with open(job.result_path, "rb") as f:
        data = f.read()
    os.remove(job.result_path)
    return Response(content=data, media_type="application/octet-stream")


# @router.post("/{project_id}/render")
# def create_render_config(*, session: SessionDep, project_id: int, config: ConfigRender):
#     config.project_id = project_id
#     return crud_config_render.create_render(session, config)
