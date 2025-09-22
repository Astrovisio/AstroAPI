from datetime import datetime
from typing import List, Optional

from sqlalchemy.orm import selectinload
from sqlmodel import Session, select

from api.error_handlers import ProjectNotFoundError
from api.models import (
    File,
    FileProjectLink,
    Project,
    ProjectCreate,
    ProjectDuplicate,
    ProjectFileVariableConfig,
    ProjectRead,
    ProjectUpdate,
    Variable,
)
from api.utils import data_processor

from .file import FileService
from .variable import VariableService


class ProjectService:
    def __init__(self, session: Session):
        self.session = session

    def create_project(self, project_data: ProjectCreate) -> ProjectRead:
        """
        Create a project with files and their variables in one transaction.
        Implements caching - reuses existing processed files.
        """
        file_variables_map = data_processor.read_data(project_data.paths)

        db_project = Project(
            name=project_data.name,
            favourite=project_data.favourite,
            description=project_data.description,
        )
        self.session.add(db_project)
        self.session.flush()  # Get the project ID without committing

        file_service = FileService(self.session)
        file_service.add_files_to_project(
            db_project.id, project_data.paths, file_variables_map
        )

        self.session.commit()
        self.session.refresh(db_project)
        return self.get_project(db_project.id)

    def get_project(self, project_id: int) -> ProjectRead:
        """Get project with all files and variables loaded."""

        statement = (
            select(Project)
            .options(selectinload(Project.files).selectinload(File.variables))
            .where(Project.id == project_id)
        )
        project = self.session.exec(statement).first()
        if not project:
            raise ProjectNotFoundError(project_id)
        project.last_opened = datetime.utcnow()
        temp_project_read = ProjectRead.model_validate(project)

        variable_service = VariableService(self.session)
        file_service = FileService(self.session)
        for file in project.files:
            file_config = file_service.get_file(project.id, file.id)
            for var in file.variables:
                cfg = self.session.exec(
                    select(ProjectFileVariableConfig).where(
                        ProjectFileVariableConfig.project_id == project.id,
                        ProjectFileVariableConfig.file_id == file.id,
                        ProjectFileVariableConfig.variable_id == var.id,
                    )
                ).first()
                for i, f in enumerate(temp_project_read.files):
                    if f.id == file.id:
                        f.downsampling = file_config.downsampling
                        f.processed = file_config.processed
                        f.processed_path = file_config.processed_path
                        f.order = file_config.order
                        for j, v in enumerate(f.variables):
                            if v.var_name == var.var_name:
                                temp_project_read.files[i].variables[j] = (
                                    variable_service.build_variable_read(var, cfg)
                                )

        return ProjectRead.model_validate(temp_project_read)

    def get_projects(self) -> List[ProjectRead]:
        """Get all projects with files and variables loaded."""

        statement = select(Project).options(
            selectinload(Project.files).selectinload(File.variables)
        )
        projects = self.session.exec(statement).all()
        pjs = [ProjectRead.model_validate(p) for p in projects]
        variable_service = VariableService(self.session)
        file_service = FileService(self.session)
        for project in projects:
            for file in project.files:
                file_config = file_service.get_file(project.id, file.id)
                variable_service.get_file_variable_configs(project.id, file.id)
                for var in file.variables:
                    cfg = self.session.exec(
                        select(ProjectFileVariableConfig).where(
                            ProjectFileVariableConfig.project_id == project.id,
                            ProjectFileVariableConfig.file_id == file.id,
                            ProjectFileVariableConfig.variable_id == var.id,
                        )
                    ).first()
                    for i, f in enumerate(
                        next(p for p in pjs if p.id == project.id).files
                    ):
                        if f.id == file.id:
                            f.downsampling = file_config.downsampling
                            f.processed = file_config.processed
                            f.processed_path = file_config.processed_path
                            f.order = file_config.order
                            for j, v in enumerate(f.variables):
                                if v.var_name == var.var_name:
                                    next(p for p in pjs if p.id == project.id).files[
                                        i
                                    ].variables[
                                        j
                                    ] = variable_service.build_variable_read(
                                        var, cfg
                                    )
        return [ProjectRead.model_validate(p) for p in pjs]

    def replace_project_files(
        self, project_id: int, new_file_paths: List[str]
    ) -> Optional[ProjectRead]:
        """Replace all files in a project with new ones."""

        db_project = self.session.get(Project, project_id)
        if not db_project:
            raise ProjectNotFoundError(project_id)

        current_file_paths = {f.path for f in db_project.files}
        new_file_paths_set = set(new_file_paths)

        # Files to remove
        files_to_remove = current_file_paths - new_file_paths_set
        if files_to_remove:
            file_service = FileService(self.session)
            file_service.remove_files_from_project(project_id, list(files_to_remove))
            self.session.commit()

        # Files to add
        files_to_add = new_file_paths_set - current_file_paths
        if files_to_add:
            file_variables_map = data_processor.read_data(list(files_to_add))
            file_service = FileService(self.session)
            file_service.add_files_to_project(
                project_id, list(files_to_add), file_variables_map
            )
            self.session.commit()

        return self.get_project(project_id)

    def update_project(
        self, project_id: int, project_update: ProjectUpdate
    ) -> Optional[ProjectRead]:
        """Update project metadata and variable configurations only."""

        db_project = self.session.get(Project, project_id)
        if not db_project:
            raise ProjectNotFoundError(project_id)

        db_project.last_opened = datetime.utcnow()

        for field, value in project_update.model_dump(exclude_unset=True).items():
            if field != "order":
                setattr(db_project, field, value)
            else:
                fpls = self.session.exec(
                    select(FileProjectLink).where(
                        FileProjectLink.project_id == project_id
                    )
                ).all()
                for fpl in fpls:
                    if fpl.file_id in value:
                        fpl.order = value.index(fpl.file_id)
                    else:
                        fpl.order = None
                    self.session.add(fpl)

        self.session.commit()
        return self.get_project(project_id)

    def delete_project(self, project_id: int) -> bool:
        """Delete project and handle cascading deletes."""
        db_project = self.session.get(Project, project_id)
        if not db_project:
            raise ProjectNotFoundError(project_id)
        if not db_project:
            return False

        self.session.delete(db_project)
        self.session.commit()

    def duplicate_project(
        self, project_id: int, project: ProjectDuplicate
    ) -> ProjectRead:
        """Duplicate a project along with its files and variable configurations."""
        db_project = self.session.get(Project, project_id)
        if not db_project:
            raise ProjectNotFoundError(project_id)

        new_project = Project(
            name=project.name,
            favourite=False,
            description=project.description,
            last_opened=datetime.utcnow(),
        )
        self.session.add(new_project)
        self.session.flush()

        for file in db_project.files:
            new_link = FileProjectLink(
                project_id=new_project.id,
                file_id=file.id,
            )
            self.session.add(new_link)

            variables = self.session.exec(
                select(Variable).where(Variable.file_id == file.id)
            ).all()
            for var in variables:
                existing_cfg = self.session.exec(
                    select(ProjectFileVariableConfig).where(
                        ProjectFileVariableConfig.project_id == db_project.id,
                        ProjectFileVariableConfig.file_id == file.id,
                        ProjectFileVariableConfig.variable_id == var.id,
                    )
                ).first()
                if existing_cfg:
                    new_cfg = ProjectFileVariableConfig(
                        project_id=new_project.id,
                        file_id=file.id,
                        variable_id=var.id,
                        thr_min_sel=existing_cfg.thr_min_sel,
                        thr_max_sel=existing_cfg.thr_max_sel,
                        selected=existing_cfg.selected,
                        x_axis=existing_cfg.x_axis,
                        y_axis=existing_cfg.y_axis,
                        z_axis=existing_cfg.z_axis,
                    )
                    self.session.add(new_cfg)

        self.session.commit()
        self.session.refresh(new_project)
        return self.get_project(new_project.id)
