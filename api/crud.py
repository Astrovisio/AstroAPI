from typing import List
from datetime import datetime
from fastapi import HTTPException
from sqlmodel import select, delete
from api.models import (
    File,
    ProjectFileLink,
    Project,
    ProjectCreate,
    ProjectRead,
    ProjectUpdate,
    ProjectFileLink,
    VariableConfig,
    ConfigProcess,
    ConfigProcessCreate,
    ConfigProcessRead,
    ConfigRender,
    ConfigRenderCreate,
    ConfigRenderRead,
)
from api.db import SessionDep


class CRUDConfigProcess:
    def get_config_process(self, db: SessionDep, project_id: int) -> ConfigProcessRead:
        config_processes = db.exec(
            select(ConfigProcess).where(ConfigProcess.project_id == project_id)
        ).all()
        return self._build_config_process_read(config_processes)

    def create_config_process(
        self, db: SessionDep, config_create: ConfigProcessCreate, project_id: int
    ) -> ConfigProcess:
        config = ConfigProcess.model_validate(config_create)
        config.project_id = project_id
        db.add(config)
        db.commit()
        db.refresh(config)
        return config

    def delete_config_process(self, db: SessionDep, project_id: int):
        config_processes = db.exec(
            select(ConfigProcess).where(ConfigProcess.project_id == project_id)
        ).all()
        for config_process in config_processes:
            db.delete(config_process)
        db.commit()

    def _build_config_process_read(
        self, config_processes: List[ConfigProcess]
    ) -> ConfigProcessRead:
        variables = {
            config.var_name: VariableConfig(
                thr_min=config.thr_min,
                thr_max=config.thr_max,
                selected=config.selected,
                x_axis=config.x_axis,
                y_axis=config.y_axis,
                z_axis=config.z_axis,
            )
            for config in config_processes
        }

        downsampling = config_processes[0].downsampling if config_processes else 1.0

        return ConfigProcessRead(downsampling=downsampling, variables=variables)


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

        config = ConfigRender.model_validate(config_create)
        db.add(config)
        db.commit()
        db.refresh(config)
        return ConfigRenderRead.model_validate(config)


crud_config_process = CRUDConfigProcess()
crud_config_render = CRUDConfigRender()


class CRUDProject:
    def get_projects(self, db: SessionDep) -> List[ProjectRead]:
        projects = db.exec(select(Project)).all()
        project_reads = []
        for project in projects:
            config_process = crud_config_process.get_config_process(db, project.id)
            project_read = ProjectRead.model_validate(project)
            project_read.paths = [file.path for file in project.files]
            project_read.config_process = config_process
            project_reads.append(project_read)
        return project_reads

    def create_project(self, db: SessionDep, project_create: ProjectCreate) -> Project:
        project = Project.model_validate(project_create)
        db.add(project)

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
        return project

    def get_project(self, db: SessionDep, project_id: int) -> ProjectRead:
        project = db.get(Project, project_id)
        if not project:
            raise HTTPException(status_code=404, detail="Project not found")
        project.last_opened = datetime.utcnow()
        db.add(project)
        db.commit()
        config_process = crud_config_process.get_config_process(db, project.id)
        project_read = ProjectRead.model_validate(project)
        project_read.paths = [file.path for file in project.files]
        project_read.config_process = config_process
        return project_read

    def update_project(
        self, db: SessionDep, project_id: int, project_update: ProjectUpdate
    ) -> Project:
        project = db.get(Project, project_id)
        if not project:
            raise HTTPException(status_code=404, detail="Project not found")

        for key, value in project_update.model_dump(exclude_unset=True).items():
            if key == "paths":
                continue
            setattr(project, key, value)

        if "paths" in project_update.model_dump(exclude_unset=True):
            ids = db.exec(
                select(ProjectFileLink.file_id).where(
                    ProjectFileLink.project_id == project_id
                )
            ).all()
            current_paths = {
                file.path
                for file in db.exec(select(File).where(File.id.in_(ids))).all()
            }
            new_paths = set(project_update.paths)

            paths_to_delete = current_paths - new_paths
            paths_to_create = new_paths - current_paths
            if paths_to_delete:
                db.exec(delete(File).where(File.path.in_(paths_to_delete)))
                db.exec(delete(ProjectFileLink).where(ProjectFileLink.file_id.in_(ids)))
                db.commit()

            for path in paths_to_create:
                file = File(path=path)
                db.add(file)
                db.commit()
                db.refresh(file)
                link = ProjectFileLink(project_id=project.id, file_id=file.id)
                db.add(link)

        db.commit()
        db.refresh(project)
        return project

    def delete_project(self, db: SessionDep, project_id: int):
        project = db.get(Project, project_id)
        if not project:
            raise HTTPException(status_code=404, detail="Project not found")
        file_ids = db.exec(
            select(ProjectFileLink.file_id).where(
                ProjectFileLink.project_id == project_id
            )
        ).all()
        db.exec(delete(File).where(File.id.in_(file_ids)))
        db.exec(delete(ConfigProcess).where(ConfigProcess.project_id == project_id))
        db.delete(project)
        db.commit()


crud_project = CRUDProject()
