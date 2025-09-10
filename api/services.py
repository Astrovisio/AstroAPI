from datetime import datetime
from typing import Dict, List, Optional

from sqlalchemy.orm import selectinload
from sqlmodel import Session, select

from api.error_handlers import (
    FileNotFoundError,
    FileProcessingError,
    ProjectNotFoundError,
    VariableNotFoundError,
)
from api.models import (
    File,
    FileCreate,
    FileProjectLink,
    FileRead,
    FileUpdate,
    ProcessJob,
    Project,
    ProjectCreate,
    ProjectRead,
    ProjectUpdate,
    ProjectVariableConfig,
    Variable,
    VariableRead,
)
from api.utils import data_processor


class ProjectService:
    def __init__(self, session: Session):
        self.session = session

    def create_project(self, project_data: ProjectCreate) -> ProjectRead:
        """
        Create a project with files and their variables in one transaction.
        Implements caching - reuses existing processed files.
        """
        file_variables_map = data_processor.read_data(project_data.file_paths)

        db_project = Project(
            name=project_data.name,
            favourite=project_data.favourite,
            description=project_data.description,
        )
        self.session.add(db_project)
        self.session.flush()  # Get the project ID without committing

        file_service = FileService(self.session)
        file_service.add_files_to_project(
            db_project.id, project_data.file_paths, file_variables_map
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
        self.session.add(project)
        self.session.commit()
        return ProjectRead.model_validate(project) if project else None

    def get_projects(self) -> List[ProjectRead]:
        """Get all projects with files and variables loaded."""

        statement = select(Project).options(
            selectinload(Project.files).selectinload(File.variables)
        )
        projects = self.session.exec(statement).all()
        return [ProjectRead.model_validate(p) for p in projects]

    def replace_project_files(
        self, project_id: int, new_file_paths: List[str]
    ) -> Optional[ProjectRead]:
        """Replace all files in a project with new ones."""

        db_project = self.session.get(Project, project_id)
        if not db_project:
            raise ProjectNotFoundError(project_id)

        current_file_paths = {f.file_path for f in db_project.files}
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
            if field != "files":
                setattr(db_project, field, value)

        if project_update.files:
            variable_service = VariableService(self.session)
            variable_service.update_project_variable_configs(
                project_id, project_update.files
            )

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


class FileService:
    def __init__(self, session: Session):
        self.session = session

    def update_file_processing_status(
        self, file_id: int, processed: bool, processed_file_path: Optional[str] = None
    ) -> Optional[FileRead]:
        """Update file processing status and cache path."""
        db_file = self.session.get(File, file_id)
        if not db_file:
            raise FileNotFoundError(file_id=file_id)

        db_file.processed = processed
        if processed_file_path:
            db_file.processed_file_path = processed_file_path

        self.session.commit()
        self.session.refresh(db_file)
        return FileRead.model_validate(db_file)

    def get_cached_file(self, file_path: str) -> Optional[FileRead]:
        """Check if file is already processed and return cached version."""
        db_file = self.session.exec(
            select(File).where(
                File.file_path == file_path,
                File.processed is True,
                File.processed_file_path.is_not(None),
            )
        ).first()

        return FileRead.model_validate(db_file) if db_file else None

    def remove_files_from_project(
        self, project_id: int, file_paths_to_remove: List[str]
    ) -> None:
        """Remove file-project links and orphaned files."""
        files_to_remove = self.session.exec(
            select(File).where(File.file_path.in_(file_paths_to_remove))
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
                select(File).where(File.file_path == file_path)
            ).first()

            if existing_file:
                db_file = existing_file
            else:
                file_type = "hdf5" if file_path.endswith(".hdf5") else "fits"
                db_file = File(
                    file_type=file_type,
                    file_path=file_path,
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


class VariableService:
    def __init__(self, session: Session):
        self.session = session

    def update_variable_selection(
        self, variable_id: int, selected: bool, **kwargs
    ) -> Optional[VariableRead]:
        """Update variable selection and other properties."""
        db_variable = self.session.get(Variable, variable_id)
        if not db_variable:
            raise VariableNotFoundError(variable_id=variable_id)

        db_variable.selected = selected
        for key, value in kwargs.items():
            if hasattr(db_variable, key):
                setattr(db_variable, key, value)

        self.session.commit()
        self.session.refresh(db_variable)
        return VariableRead.model_validate(db_variable)

    def bulk_update_variables(self, updates: List[dict]) -> List[VariableRead]:
        """Bulk update multiple variables."""
        updated_vars = []

        for update in updates:
            var_id = update.pop("id")
            db_variable = self.session.get(Variable, var_id)
            if db_variable:
                for key, value in update.items():
                    if hasattr(db_variable, key):
                        setattr(db_variable, key, value)
                updated_vars.append(db_variable)
            if not db_variable:
                raise VariableNotFoundError(variable_id=var_id)

        self.session.commit()
        return [VariableRead.model_validate(var) for var in updated_vars]

    def update_project_variable_configs(
        self, project_id: int, files_data: List[FileUpdate]
    ) -> None:
        """Update ProjectVariableConfig entries for all variables in the payload."""
        for file_data in files_data:
            db_file = self.session.exec(
                select(File).where(File.file_path == file_data.file_path)
            ).first()

            if not db_file:
                continue

            for var_data in file_data.variables:
                db_var = self.session.exec(
                    select(Variable).where(
                        Variable.file_id == db_file.id,
                        Variable.var_name == var_data.var_name,
                    )
                ).first()

                if not db_var:
                    continue

                existing_config = self.session.exec(
                    select(ProjectVariableConfig).where(
                        ProjectVariableConfig.project_id == project_id,
                        ProjectVariableConfig.variable_id == db_var.id,
                    )
                ).first()

                if existing_config:
                    existing_config.thr_min_sel = var_data.thr_min_sel
                    existing_config.thr_max_sel = var_data.thr_max_sel
                    existing_config.selected = var_data.selected
                    existing_config.x_axis = var_data.x_axis
                    existing_config.y_axis = var_data.y_axis
                    existing_config.z_axis = var_data.z_axis
                else:
                    new_config = ProjectVariableConfig(
                        project_id=project_id,
                        variable_id=db_var.id,
                        thr_min_sel=var_data.thr_min_sel,
                        thr_max_sel=var_data.thr_max_sel,
                        selected=var_data.selected,
                        x_axis=var_data.x_axis,
                        y_axis=var_data.y_axis,
                        z_axis=var_data.z_axis,
                    )
                    self.session.add(new_config)


class ProcessJobService:
    def __init__(self, session: Session):
        self.session = session

    def get_job(self, job_id: int) -> Optional[ProcessJob]:
        """Get a process job by ID"""
        return self.session.get(ProcessJob, job_id)

    def get_job_progress(self, job_id: int) -> Dict:
        """Get job progress information"""
        job = self.get_job(job_id)
        if not job:
            return {"error": "Job not found"}

        return {
            "status": job.status,
            "progress": job.progress,
            "error": job.error,
        }

    def get_job_result_path(self, job_id: int) -> Optional[str]:
        """Get job result path if completed"""
        job = self.get_job(job_id)
        if job and job.status == "done" and job.result_path:
            return job.result_path
        return None
