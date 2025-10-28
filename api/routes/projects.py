from typing import List

from fastapi import APIRouter, Response

from api.deps import FileServiceDep, ProcessJobServiceDep, ProjectServiceDep
from api.models import (
    FileRead,
    FileUpdate,
    ProjectCreate,
    ProjectDuplicate,
    ProjectFilesUpdate,
    ProjectRead,
    ProjectUpdate,
    RenderRead,
    RenderUpdate,
)

router = APIRouter(prefix="/projects", tags=["projects"])


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
def delete_project(*, project_id: int, service: ProjectServiceDep):
    """Delete a project"""
    service.delete_project(project_id)
    return {"message": "Project deleted successfully"}


@router.post("/{project_id}/duplicate", response_model=ProjectRead)
def duplicate_project(
    *, project_id: int, project: ProjectDuplicate, service: ProjectServiceDep
):
    """Delete a project"""
    return service.duplicate_project(project_id=project_id, project=project)


@router.put("/{project_id}/files", response_model=ProjectRead)
def replace_project_files(
    *, project_id: int, files_update: ProjectFilesUpdate, service: ProjectServiceDep
):
    """Replace all files in a project"""
    return service.replace_project_files(
        project_id=project_id, new_file_paths=files_update.paths
    )


@router.get("/{project_id}/file/{file_id}", response_model=FileRead)
def read_file(*, project_id: int, file_id: int, service: FileServiceDep):
    """Get a single file in a project"""
    return service.get_file(project_id=project_id, file_id=file_id)


@router.put("/{project_id}/file/{file_id}", response_model=FileRead)
def update_file(
    *, project_id: int, file_id: int, file_data: FileUpdate, service: FileServiceDep
):
    """Update a file in a project"""
    return service.update_file(
        project_id=project_id, file_id=file_id, file_update=file_data
    )


@router.get("/{project_id}/file/{file_id}/process")
def processed_file(*, project_id: int, file_id: int, service: FileServiceDep):
    """Get processed file"""

    file = service.get_cached_file(project_id=project_id, file_id=file_id)
    if not file:
        return Response(
            content="File not found", status_code=404, media_type="text/plain"
        )
    if not file.processed:
        return Response(
            content="File not processed yet",
            status_code=400,
            media_type="text/plain",
        )

    with open(file.processed_path, "rb") as f:
        data = f.read()
    return Response(content=data, media_type="application/octet-stream")


@router.post("/{project_id}/file/{file_id}/process")
def process_file(
    *,
    project_id: int,
    file_id: int,
    pjservice: ProcessJobServiceDep,
    fservice: FileServiceDep,
):
    """Start processing a file"""

    job_id = pjservice.start_file_processing(project_id=project_id, file_id=file_id)

    fservice.create_render(project_id=project_id, file_id=file_id)

    return {"job_id": job_id}


@router.get("/{project_id}/file/{file_id}/render", response_model=RenderRead)
def get_render(*, project_id: int, file_id: int, service: FileServiceDep):
    """Get render settings for a file in a project"""
    return service.get_render(project_id=project_id, file_id=file_id)


@router.put("/{project_id}/file/{file_id}/render", response_model=RenderRead)
def update_render(
    *, project_id: int, file_id: int, render_data: RenderUpdate, service: FileServiceDep
):
    """Update render settings for a file in a project"""
    return service.update_render(
        project_id=project_id, file_id=file_id, render_data=render_data
    )
