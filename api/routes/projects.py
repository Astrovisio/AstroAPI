import logging
import os
from threading import Thread
from typing import List

import msgpack
from fastapi import APIRouter, HTTPException, Response

from api.db import ProjectServiceDep, SessionLocal
from api.exceptions import ProjectNotFoundError
from api.models import (
    FileUpdate,
    ProjectCreate,
    ProjectFilesUpdate,
    ProjectRead,
    ProjectUpdate,
)
from api.utils import data_processor

router = APIRouter(prefix="/projects", tags=["projects"])
logger = logging.getLogger(__name__)


@router.get("/", response_model=List[ProjectRead])
def read_projects(*, service: ProjectServiceDep):
    """Get all projects"""
    return service.get_projects()


@router.post("/", response_model=ProjectRead)
def create_project(*, project_data: ProjectCreate, service: ProjectServiceDep):
    """Create a new project with files and variables."""

    return service.create_project(project_data=project_data)


@router.get("/{project_id}", response_model=ProjectRead)
def read_project(*, project_id: int, service: ProjectServiceDep):
    """Get a single project"""
    return service.get_project(project_id=project_id)


@router.put("/{project_id}", response_model=ProjectRead)
def update_project(
    *, project_id: int, project: ProjectUpdate, service: ProjectServiceDep
):
    """Update project and optionally its files"""
    return service.update_project(project_id=project_id, project_update=project)


@router.put("/{project_id}/files", response_model=ProjectRead)
def replace_project_files(
    *, project_id: int, files_update: ProjectFilesUpdate, service: ProjectServiceDep
):
    """Replace all files in a project"""
    return service.replace_project_files(project_id, files_update.file_paths)


#
#
# @router.delete("/{project_id}")
# def remove_project(*, session: SessionDep, project_id: int):
#     """Delete a project"""
#     crud_project.delete_project(session, project_id)
#     return {"message": "Project deleted successfully"}
#
#
# # File-level operations
# @router.put("/{project_id}/files/{file_id}")
# def update_file_config(
#     *, session: SessionDep, project_id: int, file_id: int, file_update: FileUpdate
# ):
#     """Update file-level configuration (e.g., downsampling)"""
#     crud_project_file.update_file(
#         session, file_id, **file_update.model_dump(exclude_unset=True)
#     )
#     return {"message": "File updated successfully"}
#
#
# @router.put("/{project_id}/files/{file_id}/variables/{var_name}")
# def update_variable_config(
#     *,
#     session: SessionDep,
#     project_id: int,
#     file_id: int,
#     var_name: str,
#     variable_update: VariableConfigUpdate,
# ):
#     """Update variable configuration for a specific file"""
#     crud_project_file.update_variable(
#         session, file_id, var_name, **variable_update.model_dump(exclude_unset=True)
#     )
#     return {"message": "Variable updated successfully"}
#
#
# # Processing operations
# @router.post("/{project_id}/process")
# def process_project(*, session: SessionDep, project_id: int):
#     """Start processing a project"""
#     project_data = crud_project.get_project(session, project_id)
#     job = crud_process_job.create_process_job(session, project_id)
#
#     def run_processing(job_id, session_maker, project_data):
#         session = session_maker()
#         try:
#
#             def progress_callback(progress):
#                 progress = round(progress, 2)
#                 crud_process_job.update_process_job(session, job_id, progress=progress)
#
#             crud_process_job.update_process_job(
#                 session, job_id, status="processing", progress=0.1
#             )
#
#             # Process each file separately
#             all_processed_data = []
#             total_files = len(project_data.files)
#
#             for i, file_data in enumerate(project_data.files):
#                 file_progress_start = i / total_files
#                 file_progress_end = (i + 1) / total_files
#
#                 def file_progress_callback(file_progress):
#                     overall_progress = file_progress_start + (
#                         file_progress * (file_progress_end - file_progress_start)
#                     )
#                     progress_callback(overall_progress)
#
#                 # Process this file
#                 processed_file_data = data_processor.process_file(
#                     file_data.path,
#                     file_data.downsampling,
#                     {var.var_name: var for var in file_data.variables},
#                     progress_callback=file_progress_callback,
#                 )
#                 all_processed_data.append(processed_file_data)
#
#             # Combine results
#             result_path = f"./data/project_{project_data.id}_processed.msgpack"
#             combined_data = data_processor.combine_processed_files(all_processed_data)
#
#             data_dict = {
#                 "columns": combined_data.columns,
#                 "rows": combined_data.to_numpy().tolist(),
#             }
#             binary_data = msgpack.packb(data_dict, use_bin_type=True)
#             with open(result_path, "wb") as f:
#                 f.write(binary_data)
#
#             crud_process_job.update_process_job(
#                 session, job_id, status="done", progress=1.0, result_path=result_path
#             )
#         except Exception as e:
#             crud_process_job.update_process_job(
#                 session, job_id, status="error", error=str(e), progress=1.0
#             )
#         finally:
#             session.close()
#
#     Thread(target=run_processing, args=(job.id, SessionLocal, project_data)).start()
#     return {"job_id": job.id}
#
#
# @router.get("/{project_id}/process/{job_id}/progress")
# def process_progress(*, session: SessionDep, project_id: int, job_id: int):
#     """Get processing progress"""
#     job = crud_process_job.get_process_job(session, job_id)
#     if not job:
#         return {"error": "Job not found"}
#     return {
#         "status": job.status,
#         "progress": job.progress,
#         "error": job.error,
#     }
#
#
# @router.get("/{project_id}/process/{job_id}/result", response_class=Response)
# def process_result(*, session: SessionDep, project_id: int, job_id: int):
#     """Get processing result"""
#     job = crud_process_job.get_process_job(session, job_id)
#     if not job or job.status != "done" or not job.result_path:
#         return Response(
#             content="Job not found or not completed",
#             status_code=404,
#             media_type="text/plain",
#         )
#     with open(job.result_path, "rb") as f:
#         data = f.read()
#     os.remove(job.result_path)
#     return Response(content=data, media_type="application/octet-stream")
