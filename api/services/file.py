import os
from datetime import datetime
from typing import Dict, List

from sqlalchemy.orm import selectinload
from sqlmodel import Session, select

from api.error_handlers import FileNotFoundError, ProjectNotFoundError
from api.models import (
    File,
    FileCreate,
    FileProjectLink,
    FileRead,
    FileUpdate,
    Project,
    ProjectFileVariableConfig,
    RenderBase,
    RenderRead,
    RenderSettings,
    RenderUpdate,
    Variable,
)

from .variable import VariableService


class FileService:
    def __init__(self, session: Session):
        self.session = session

    def get_file(self, project_id: int, file_id: int) -> FileRead:
        """Get a single file in a project with its variable configurations."""
        db_project = self.session.get(Project, project_id)
        if not db_project:
            raise ProjectNotFoundError(project_id=project_id)
        db_project.last_opened = datetime.utcnow()
        self.session.commit()

        db_file = self.session.exec(
            select(File, FileProjectLink)
            .options(selectinload(File.variables))
            .join(FileProjectLink)
            .where(
                File.id == file_id,
                FileProjectLink.project_id == project_id,
            )
        ).first()

        if not db_file:
            raise FileNotFoundError(file_id=file_id)

        file_obj, file_project_link_obj = db_file
        file_read = FileRead.model_validate(file_obj)
        file_read.processed = file_project_link_obj.processed
        file_read.downsampling = file_project_link_obj.downsampling
        file_read.processed_path = file_project_link_obj.processed_path
        file_read.order = file_project_link_obj.order

        variable_service = VariableService(self.session)
        for var in file_obj.variables:
            cfg = self.session.exec(
                select(ProjectFileVariableConfig).where(
                    ProjectFileVariableConfig.project_id == project_id,
                    ProjectFileVariableConfig.file_id == file_id,
                    ProjectFileVariableConfig.variable_id == var.id,
                )
            ).first()
            for i, v in enumerate(file_read.variables):
                if v.var_name == var.var_name:
                    file_read.variables[i] = variable_service.build_variable_read(
                        var, cfg
                    )

        return file_read

    def update_file(
        self, project_id: int, file_id: int, file_update: FileUpdate
    ) -> FileRead:
        """Update file and its variable configurations for a specific project."""

        db_file = self.session.get(File, file_id)
        if not db_file:
            raise FileNotFoundError(file_id=file_id)
        file_config = self.session.exec(
            select(FileProjectLink).where(
                FileProjectLink.project_id == project_id,
                FileProjectLink.file_id == file_id,
            )
        ).first()
        file_config.processed = False
        os.remove(file_config.processed_path) if file_config.processed_path else None
        file_config.processed_path = None
        file_config.order = file_update.order

        db_project = self.session.get(Project, project_id)
        if not db_project:
            raise ProjectNotFoundError(project_id=project_id)
        db_project.last_opened = datetime.utcnow()

        if "downsampling" in file_update.model_dump(exclude_unset=True):
            if file_update.downsampling <= 0 or file_update.downsampling > 1:
                raise ValueError("Downsampling must be between 0 (exclusive) and 1.")

            file_config.downsampling = file_update.downsampling

        if file_update.variables:
            variable_service = VariableService(self.session)
            variable_service.update_file_variable_configs(
                project_id, file_id, file_update
            )

        self.delete_renders(project_id, file_id)
        self.session.add(file_config)
        self.session.commit()
        self.session.refresh(file_config)
        file_read = FileRead.model_validate(db_file)
        file_read.processed = file_config.processed
        file_read.downsampling = file_config.downsampling
        file_read.processed_path = file_config.processed_path
        file_read.order = file_config.order

        variable_service = VariableService(self.session)
        for var in db_file.variables:
            cfg = self.session.exec(
                select(ProjectFileVariableConfig).where(
                    ProjectFileVariableConfig.project_id == project_id,
                    ProjectFileVariableConfig.file_id == file_id,
                    ProjectFileVariableConfig.variable_id == var.id,
                )
            ).first()
            for i, v in enumerate(file_read.variables):
                if v.var_name == var.var_name:
                    file_read.variables[i] = variable_service.build_variable_read(
                        var, cfg
                    )

        return FileRead.model_validate(file_read)

    def get_cached_file(self, project_id: int, file_id: int) -> FileRead:
        """Check if file is already processed and return it."""
        db_file = self.session.exec(
            select(File, FileProjectLink)
            .join(FileProjectLink)
            .where(File.id == file_id, FileProjectLink.project_id == project_id)
        ).first()

        file_read = FileRead.model_validate(db_file[0])
        file_read.processed = db_file[1].processed
        file_read.downsampling = db_file[1].downsampling
        file_read.processed_path = db_file[1].processed_path
        return file_read

    def remove_files_from_project(
        self, project_id: int, file_paths_to_remove: List[str]
    ) -> None:
        """Remove file-project links and orphaned files."""
        files_to_remove = self.session.exec(
            select(File).where(File.path.in_(file_paths_to_remove))
        ).all()

        for db_file in files_to_remove:
            link = self.session.exec(
                select(FileProjectLink).where(
                    FileProjectLink.project_id == project_id,
                    FileProjectLink.file_id == db_file.id,
                )
            ).first()
            if link:
                self.session.delete(link)

            remaining_links = self.session.exec(
                select(FileProjectLink).where(FileProjectLink.file_id == db_file.id)
            ).all()

            if not remaining_links:
                self.session.delete(db_file)

    def add_files_to_project(
        self,
        project_id: int,
        new_file_paths: List[str],
        file_variables_map: Dict[str, FileCreate],
    ) -> None:
        """Add new files to project with their variables."""
        for file_path in new_file_paths:
            existing_file = self.session.exec(
                select(File).where(File.path == file_path)
            ).first()

            if existing_file:
                db_file = existing_file
            else:
                file_type = "hdf5" if file_path.endswith(".hdf5") else "fits"
                db_file = File(
                    type=file_type,
                    name=file_variables_map[file_path].name,
                    path=file_path,
                    size=file_variables_map[file_path].size,
                )
                self.session.add(db_file)
                self.session.flush()

                for var_data in file_variables_map[file_path].variables:
                    db_variable = Variable(
                        file_id=db_file.id,
                        var_name=var_data.var_name,
                        unit=var_data.unit,
                        thr_min=var_data.thr_min,
                        thr_max=var_data.thr_max,
                    )
                    self.session.add(db_variable)

            existing_link = self.session.exec(
                select(FileProjectLink).where(
                    FileProjectLink.project_id == project_id,
                    FileProjectLink.file_id == db_file.id,
                )
            ).first()

            if not existing_link:
                link = FileProjectLink(project_id=project_id, file_id=db_file.id)
                self.session.add(link)

    def create_render(self, project_id: int, file_id: int) -> None:
        """Create default render settings for a specific file"""
        cfgs = self.session.exec(
            select(ProjectFileVariableConfig).where(
                ProjectFileVariableConfig.project_id == project_id,
                ProjectFileVariableConfig.file_id == file_id,
                ProjectFileVariableConfig.selected == 1,
            )
        ).all()
        for cfg in cfgs:
            render = RenderSettings(
                config_id=cfg.id,
                vis_thr_min=cfg.thr_min_sel,
                vis_thr_max=cfg.thr_max_sel,
            )
            self.session.add(render)

        self.session.commit()

    def get_render(self, project_id: int, file_id: int) -> RenderRead:
        """Get render settings for a specific file"""
        cfgs = self.session.exec(
            select(ProjectFileVariableConfig, Variable.var_name)
            .join(Variable, ProjectFileVariableConfig.variable_id == Variable.id)
            .where(
                ProjectFileVariableConfig.project_id == project_id,
                ProjectFileVariableConfig.file_id == file_id,
                ProjectFileVariableConfig.selected == 1,
            )
        ).all()
        renders = self.session.exec(
            select(RenderSettings).where(
                RenderSettings.config_id.in_([cfg[0].id for cfg in cfgs])
            )
        ).all()
        render_reads = []
        for render in renders:
            cfg_tuple = next((c for c in cfgs if c[0].id == render.config_id), None)
            if cfg_tuple:
                render_base = RenderBase(var_name=cfg_tuple[1], **render.model_dump())
                render_reads.append(render_base)
        return RenderRead(variables=render_reads)

    def update_render(
        self, project_id: int, file_id: int, render_data: RenderUpdate
    ) -> RenderRead:
        """Update render settings for a specific file"""
        cfgs = self.session.exec(
            select(ProjectFileVariableConfig, Variable.var_name)
            .join(Variable, ProjectFileVariableConfig.variable_id == Variable.id)
            .where(
                ProjectFileVariableConfig.project_id == project_id,
                ProjectFileVariableConfig.file_id == file_id,
                ProjectFileVariableConfig.selected == 1,
            )
        ).all()
        renders = self.session.exec(
            select(RenderSettings).where(
                RenderSettings.config_id.in_([cfg[0].id for cfg in cfgs])
            )
        ).all()
        render_reads = []
        for variable in render_data.variables:
            cfg_tuple = next(
                (c for c in cfgs if c[1] == variable.var_name),
                None,
            )
            if not cfg_tuple:
                continue
            cfg = cfg_tuple[0]
            render = next((r for r in renders if r.config_id == cfg.id), None)
            for key, value in variable.model_dump(exclude={"var_name"}).items():
                if value is not None:
                    setattr(render, key, value)
            self.session.add(render)
            render_read = RenderBase(var_name=variable.var_name, **render.model_dump())
            render_reads.append(render_read)
        self.session.commit()
        return RenderRead(variables=render_reads)

    def delete_renders(self, project_id: int, file_id: int) -> None:
        """Delete render settings for a specific file"""
        cfgs = self.session.exec(
            select(ProjectFileVariableConfig).where(
                ProjectFileVariableConfig.project_id == project_id,
                ProjectFileVariableConfig.file_id == file_id,
                ProjectFileVariableConfig.selected == 1,
            )
        ).all()
        renders = self.session.exec(
            select(RenderSettings).where(
                RenderSettings.config_id.in_([cfg.id for cfg in cfgs])
            )
        ).all()
        for render in renders:
            self.session.delete(render)
        self.session.commit()
