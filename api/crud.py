from typing import List
from fastapi import HTTPException
from sqlmodel import select
from api.models import (
    File,
    Project,
    ProjectCreate,
    ProjectRead,
    ProjectFileLink,
    ConfigProcess,
    ConfigProcessCreate,
    ConfigProcessRead,
    ConfigRender,
    ConfigRenderCreate,
    ConfigRenderRead,
)
from api.db import SessionDep


class CRUDProject:
    def get_projects(self, db: SessionDep) -> List[ProjectRead]:
        projects = db.exec(select(Project)).all()
        project_reads = []
        for project in projects:
            project_read = ProjectRead.from_orm(project)
            project_read.paths = [file.path for file in project.files]
            project_reads.append(project_read)
        return project_reads

    def create_project(
        self, db: SessionDep, project_create: ProjectCreate
    ) -> ProjectRead:
        project = Project.from_orm(project_create)
        db.add(project)
        db.commit()
        db.refresh(project)

        for path in project_create.paths:
            file = db.exec(select(File).where(File.path == path)).first()
            if not file:
                file = File(path=path)
                db.add(file)
                db.commit()
                db.refresh(file)
            link = ProjectFileLink(project_id=project.id, file_id=file.id)
            db.add(link)

        db.commit()
        db.refresh(project)
        project_read = ProjectRead.from_orm(project)
        project_read.paths = project_create.paths
        return project_read

    def get_project(self, db: SessionDep, project_id: int) -> ProjectRead:
        project = db.get(Project, project_id)
        if not project:
            raise HTTPException(status_code=404, detail="Project not found")
        project_read = ProjectRead.from_orm(project)
        project_read.paths = [file.path for file in project.files]
        return project_read

    def delete_project(self, db: SessionDep, project_id: int):
        project = db.get(Project, project_id)
        if not project:
            raise HTTPException(status_code=404, detail="Project not found")
        db.delete(project)
        db.commit()


class CRUDConfigProcess:
    def create_process(
        self, db: SessionDep, config_create: ConfigProcessCreate
    ) -> ConfigProcessRead:
        config = ConfigProcess.from_orm(config_create)
        db.add(config)
        db.commit()
        db.refresh(config)
        return ConfigProcessRead.from_orm(config)


class CRUDConfigRender:
    def create_render(
        self, db: SessionDep, config_create: ConfigRenderCreate
    ) -> ConfigRenderRead:
        config_process = db.exec(
            select(ConfigProcess).where(
                ConfigProcess.project_id == config_create.project_id,
                ConfigProcess.var_name == config_create.var_name,
            )
        ).first()

        if not config_process:
            raise HTTPException(
                status_code=404,
                detail="ConfigProcess not found for the given project_id and var_name",
            )

        config_create.thr_min = config_process.thr_min
        config_create.thr_max = config_process.thr_max

        config = ConfigRender.from_orm(config_create)
        db.add(config)
        db.commit()
        db.refresh(config)
        return ConfigRenderRead.from_orm(config)


crud_project = CRUDProject()
crud_config_process = CRUDConfigProcess()
crud_config_render = CRUDConfigRender()
