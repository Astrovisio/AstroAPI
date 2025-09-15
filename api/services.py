import os
from datetime import datetime
from threading import Thread
from typing import Dict, List, Optional

import msgpack
from sqlalchemy.orm import selectinload
from sqlmodel import Session, select

from api.db import SessionLocal
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
    ProjectFileVariableConfig,
    ProjectRead,
    ProjectUpdate,
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
                            for j, v in enumerate(f.variables):
                                if v.var_name == var.var_name:
                                    next(p for p in pjs if p.id == project.id).files[
                                        i
                                    ].variables[
                                        j
                                    ] = variable_service.build_variable_read(
                                        var, cfg
                                    )
        return pjs

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
            if field != "files":
                setattr(db_project, field, value)

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

    def duplicate_project(self, project_id: int) -> ProjectRead:
        """Duplicate a project along with its files and variable configurations."""
        db_project = self.session.get(Project, project_id)
        if not db_project:
            raise ProjectNotFoundError(project_id)

        new_project = Project(
            name=f"{db_project.name} (Copy)",
            favourite=db_project.favourite,
            description=db_project.description,
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

        self.session.commit()
        self.session.refresh(db_file)
        self.session.refresh(file_config)
        file_read = FileRead.model_validate(db_file)
        file_read.processed = file_config.processed
        file_read.downsampling = file_config.downsampling
        file_read.processed_path = file_config.processed_path

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
                    path=file_path,
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

    def update_file_variable_configs(
        self, project_id: int, file_id: int, file_data: FileUpdate
    ) -> None:
        """Update ProjectFileVariableConfig entries for all variables in the payload."""
        db_file = self.session.exec(select(File).where(File.id == file_id)).first()

        if not db_file:
            raise FileNotFoundError(file_id=file_id)

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
                select(ProjectFileVariableConfig).where(
                    ProjectFileVariableConfig.project_id == project_id,
                    ProjectFileVariableConfig.file_id == file_id,
                    ProjectFileVariableConfig.variable_id == db_var.id,
                )
            ).first()

            if existing_config:
                existing_config.thr_min_sel = var_data.thr_min_sel
                existing_config.thr_max_sel = var_data.thr_max_sel
                existing_config.selected = var_data.selected
                existing_config.x_axis = var_data.x_axis
                existing_config.y_axis = var_data.y_axis
                existing_config.z_axis = var_data.z_axis
                self.session.add(existing_config)
            else:
                new_config = ProjectFileVariableConfig(
                    project_id=project_id,
                    file_id=file_id,
                    variable_id=db_var.id,
                    thr_min_sel=var_data.thr_min_sel,
                    thr_max_sel=var_data.thr_max_sel,
                    selected=var_data.selected,
                    x_axis=var_data.x_axis,
                    y_axis=var_data.y_axis,
                    z_axis=var_data.z_axis,
                )
                self.session.add(new_config)
            self.session.commit()

    def get_file_variable_configs(
        self, project_id: int, file_id: int
    ) -> List[ProjectFileVariableConfig]:
        """Get ProjectVariableConfig entries for a specific file in a project."""
        configs = self.session.exec(
            select(ProjectFileVariableConfig).where(
                ProjectFileVariableConfig.project_id == project_id,
                ProjectFileVariableConfig.file_id == file_id,
            )
        ).all()
        return list(configs)

    def build_variable_read(
        self, var: Variable, cfg: ProjectFileVariableConfig
    ) -> VariableRead:
        """Helper to build VariableRead from Variable and its config."""
        return VariableRead(
            var_name=var.var_name,
            unit=var.unit,
            thr_min=var.thr_min,
            thr_max=var.thr_max,
            thr_min_sel=cfg.thr_min_sel if cfg else None,
            thr_max_sel=cfg.thr_max_sel if cfg else None,
            selected=cfg.selected if cfg else False,
            x_axis=cfg.x_axis if cfg else False,
            y_axis=cfg.y_axis if cfg else False,
            z_axis=cfg.z_axis if cfg else False,
        )


class ProcessJobService:
    def __init__(self, session: Session):
        self.session = session

    def get_job(self, job_id: int) -> ProcessJob:
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

    def start_file_processing(self, project_id: int, file_id: int) -> int:
        """Start processing a single file in the background"""
        file_service = FileService(self.session)

        file_data = file_service.get_file(project_id, file_id)
        if not file_data:
            raise ValueError(
                f"File with id {file_id} not found in project {project_id}"
            )

        new_job = ProcessJob(
            project_id=project_id, file_id=file_id, status="pending", progress=0.0
        )
        self.session.add(new_job)
        self.session.commit()
        self.session.refresh(new_job)

        job_id = new_job.id

        thread = Thread(
            target=self._run_file_processing,
            args=(job_id, project_id, file_data),
            daemon=True,
        )
        thread.start()

        return job_id

    def _run_file_processing(self, job_id: int, project_id: int, file_data: FileRead):
        """Run the actual file processing in background thread"""
        with SessionLocal() as session:
            try:

                def progress_callback(progress: float):
                    progress = round(progress, 2)
                    self._update_job_progress(job_id, progress)

                self._update_job_status(job_id, "processing")

                processed_file_data = data_processor.process_data(
                    file_config=file_data,
                    progress_callback=progress_callback,
                )

                result_path = f"./data/astrovisio_files/project_{project_id}_file_{file_data.id}_processed.msgpack"

                data_dict = {
                    "columns": processed_file_data.columns,
                    "rows": processed_file_data.to_numpy().tolist(),
                }
                binary_data = msgpack.packb(data_dict, use_bin_type=True)

                with open(result_path, "wb") as f:
                    f.write(binary_data)

                with SessionLocal() as update_session:
                    statement = select(FileProjectLink).where(
                        FileProjectLink.project_id == project_id,
                        FileProjectLink.file_id == file_data.id,
                    )
                    file_link = update_session.exec(statement).first()
                    file_link.processed = True
                    file_link.processed_path = result_path
                    update_session.add(file_link)
                    update_session.commit()

                self._update_job_completion(job_id, result_path)

            except Exception as e:
                self._update_job_error(job_id, str(e))

                self._update_job_completion(job_id, result_path)

            except Exception as e:
                self._update_job_error(job_id, str(e))

    def _update_job_progress(self, job_id: int, progress: float):
        """Update job progress"""
        with SessionLocal() as session:
            job = session.get(ProcessJob, job_id)
            if job:
                job.progress = progress
                session.commit()

    def _update_job_status(self, job_id: int, status: str, progress: float = None):
        """Update job status and optionally progress"""
        with SessionLocal() as session:
            job = session.get(ProcessJob, job_id)
            if job:
                job.status = status
                if progress is not None:
                    job.progress = progress
                session.commit()

    def _update_job_completion(self, job_id: int, result_path: str):
        """Mark job as completed with result path"""
        with SessionLocal() as session:
            job = session.get(ProcessJob, job_id)
            if job:
                job.status = "done"
                job.progress = 1.0
                job.result_path = result_path
                session.commit()

    def _update_job_error(self, job_id: int, error_message: str):
        """Mark job as failed with error message"""
        with SessionLocal() as session:
            job = session.get(ProcessJob, job_id)
            if job:
                job.status = "error"
                job.progress = 1.0
                job.error = error_message
                session.commit()
