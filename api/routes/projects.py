import logging
from typing import List

from fastapi import APIRouter

from api.background_tasks import BackgroundTaskService
from api.db import FileServiceDep, ProcessJobServiceDep, ProjectServiceDep
from api.models import (
    FileRead,
    FileUpdate,
    ProjectCreate,
    ProjectFilesUpdate,
    ProjectRead,
    ProjectUpdate,
)

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


@router.delete("/{project_id}")
def remove_project(*, project_id: int, service: ProjectServiceDep):
    """Delete a project"""
    service.delete_project(project_id)
    return {"message": "Project deleted successfully"}


@router.put("/{project_id}/files", response_model=ProjectRead)
def replace_project_files(
    *, project_id: int, files_update: ProjectFilesUpdate, service: ProjectServiceDep
):
    """Replace all files in a project"""
    return service.replace_project_files(
        project_id=project_id, new_file_paths=files_update.file_paths
    )


@router.get("/{project_id}/file/{file_id}", response_model=FileRead)
def read_file(*, project_id: int, file_id: int, service: FileServiceDep):
    """Get a single file in a project"""
    return service.get_file(project_id=project_id, file_id=file_id)


@router.put("/{project_id}/file/{file_id}", response_model=FileRead)
def update_file(
    *, project_id: int, file_id: int, file_data: FileUpdate, service: FileServiceDep
):
    """Replace all files in a project"""
    return service.update_file(
        project_id=project_id, file_id=file_id, file_update=file_data
    )


# Processing operations
@router.post("/{project_id}/file/{file_id}/process")
def process_project(*, project_id: int, file_id: int, service: ProcessJobServiceDep):
    # FIX: this
    """Start processing a project"""

    job_id = service.start_project_processing(project_id=project_id, file_id=file_id)

    return {"job_id": job_id}


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
