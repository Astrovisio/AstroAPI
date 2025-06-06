from datetime import datetime
from typing import List

from fastapi import HTTPException
from sqlmodel import delete, select

from api.db import SessionDep
from api.models import (ConfigFileLink, ConfigProcess, ConfigProcessCreate,
                        ConfigProcessRead, ConfigRender, ConfigRenderCreate,
                        ConfigRenderRead, File, Project, ProjectCreate,
                        ProjectFileLink, ProjectRead, ProjectUpdate,
                        VariableConfig, VariableConfigRead)
from api.utils import data_processor


class CRUDConfigProcess:
    def get_config_process(self, db: SessionDep, project_id: int) -> ConfigProcessRead:
        return self._build_config_process_read(db, project_id)

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

    def associate_config_file(self, db: SessionDep, config_id: int, file_path: str):
        file = db.exec(select(File).where(File.path == file_path)).first()
        link = ConfigFileLink(config_id=config_id, file_id=file.id)
        db.add(link)
        db.commit()

    def _build_config_process_read(
        self, db: SessionDep, project_id: int
    ) -> ConfigProcessRead:

        config_processes = db.exec(
            select(ConfigProcess).where(ConfigProcess.project_id == project_id)
        ).all()

        variables = {}
        for config in config_processes:
            if config.var_name not in variables:
                variables[config.var_name] = VariableConfigRead(**config.model_dump())
                variables[config.var_name].files = [file.path for file in config.files]
            else:
                variables[config.var_name].thr_min = min(
                    variables[config.var_name].thr_min, config.thr_min
                )
                variables[config.var_name].thr_max = max(
                    variables[config.var_name].thr_max, config.thr_max
                )
                variables[config.var_name].files.extend(
                    [file.path for file in config.files]
                )

        downsampling = config_processes[0].downsampling if config_processes else 1.0

        return ConfigProcessRead(downsampling=downsampling, variables=variables)


crud_config_process = CRUDConfigProcess()


def update_project_paths(
    db: SessionDep, project: Project, project_paths: List[str]
) -> None:
    ids = db.exec(
        select(ProjectFileLink.file_id).where(ProjectFileLink.project_id == project.id)
    ).all()
    current_paths = {
        file.path for file in db.exec(select(File).where(File.id.in_(ids))).all()
    }
    new_paths = set(project_paths)

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

    confs = data_processor.read_data(project.files)
    crud_config_process.delete_config_process(db, project.id)
    for file, vars in confs.items():
        for var_name, conf in vars.items():
            conf_db = crud_config_process.create_config_process(db, conf, project.id)
            crud_config_process.associate_config_file(db, conf_db.id, file)


def update_project_config(
    db: SessionDep, project_id: int, config_process: ConfigProcessRead
) -> None:
    config_processes = db.exec(
        select(ConfigProcess).where(ConfigProcess.project_id == project_id)
    ).all()

    for config in config_processes:
        var_config_update = VariableConfig(
            **config_process.variables.get(config.var_name).model_dump()
        )
        for k, v in var_config_update.model_dump().items():
            if k == "thr_min_sel" and v is not None:
                if v < config.thr_min:
                    v = config.thr_min
            if k == "thr_max_sel" and v is not None:
                if v > config.thr_max:
                    v = config.thr_max
            setattr(config, k, v)

        config.downsampling = config_process.downsampling
        db.add(config)
        db.commit()


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
        project.last_opened = datetime.utcnow()

        # Update fields that are not paths or config_process
        for key, value in project_update.model_dump(exclude_unset=True).items():
            if key == "paths" or key == "config_process":
                continue
            setattr(project, key, value)

        # Update paths
        project_paths = [file.path for file in project.files]
        if project_paths != project_update.paths:
            print(f"Paths changed: {project_paths} -> {project_update.paths}")
            update_project_paths(db, project, project_update.paths)
            return project

        # Update config_process
        project_config_process = crud_config_process.get_config_process(db, project.id)
        if project_config_process != project_update.config_process:
            update_project_config(db, project.id, project_update.config_process)

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
        config_ids = db.exec(
            select(ConfigProcess.id).where(ConfigProcess.project_id == project_id)
        ).all()
        db.exec(delete(ProjectFileLink).where(ProjectFileLink.project_id == project_id))
        db.exec(delete(ConfigProcess).where(ConfigProcess.project_id == project_id))
        db.exec(delete(ConfigFileLink).where(ConfigFileLink.config_id.in_(config_ids)))
        db.delete(project)
        db.commit()


crud_project = CRUDProject()


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


crud_config_render = CRUDConfigRender()
