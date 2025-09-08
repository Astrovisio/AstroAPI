from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

from sqlmodel import delete, select

from api.db import SessionDep
from api.exceptions import DataProcessingError, ProjectNotFoundError
from api.models import (
    ConfigRender,
    File,
    FileVariable,
    FileVariableRead,
    ProcessJob,
    Project,
    ProjectCreate,
    ProjectFile,
    ProjectFileLink,
    ProjectFileRead,
    ProjectRead,
    ProjectUpdate,
)
from api.utils import data_processor


class CRUDProject:
    def get_projects(self, db: SessionDep) -> List[ProjectRead]:
        """Get all projects with their files and variables"""
        projects = db.exec(select(Project)).all()
        return [self._build_project_read(db, project) for project in projects]

    def create_project(
        self, db: SessionDep, project_create: ProjectCreate
    ) -> ProjectRead:
        """Create a new project with files and variables"""
        # Create project
        project = Project(
            name=project_create.name,
            description=project_create.description,
            favourite=project_create.favourite,
        )
        db.add(project)
        db.flush()  # Get the ID

        # Process files and create the structure
        self._create_project_files(db, project.id, project_create.file_paths)

        db.commit()
        db.refresh(project)
        return self._build_project_read(db, project)

    def get_project(self, db: SessionDep, project_id: int) -> ProjectRead:
        """Get a single project by ID"""
        project = db.get(Project, project_id)
        if not project:
            raise ProjectNotFoundError(project_id)

        # Update last opened
        project.last_opened = datetime.utcnow()
        db.add(project)
        db.commit()

        return self._build_project_read(db, project)

    def update_project(
        self, db: SessionDep, project_id: int, project_update: ProjectUpdate
    ) -> ProjectRead:
        """Update project and optionally its files"""
        project = db.get(Project, project_id)
        if not project:
            raise ProjectNotFoundError(project_id)

        # Update basic project fields
        update_data = project_update.model_dump(
            exclude_unset=True, exclude={"file_paths"}
        )
        for field, value in update_data.items():
            setattr(project, field, value)

        project.last_opened = datetime.utcnow()
        db.add(project)

        # Update files if provided
        if project_update.file_paths is not None:
            self._update_project_files(db, project_id, project_update.file_paths)

        db.commit()
        db.refresh(project)
        return self._build_project_read(db, project)

    def delete_project(self, db: SessionDep, project_id: int):
        """Delete project and all related data"""
        project = db.get(Project, project_id)
        if not project:
            raise ProjectNotFoundError(project_id)

        # Delete in correct order due to foreign keys
        db.exec(
            delete(FileVariable).where(
                FileVariable.file_id.in_(
                    select(ProjectFile.id).where(ProjectFile.project_id == project_id)
                )
            )
        )
        db.exec(delete(ProjectFile).where(ProjectFile.project_id == project_id))
        db.exec(delete(ConfigRender).where(ConfigRender.project_id == project_id))
        db.exec(delete(ProcessJob).where(ProcessJob.project_id == project_id))
        db.delete(project)
        db.commit()

    def _create_project_files(
        self, db: SessionDep, project_id: int, file_paths: List[str]
    ):
        """Create files and their variables from file paths"""
        if not file_paths:
            return

        try:
            # Read data from files to discover variables
            files_data = data_processor.read_data(file_paths)
        except Exception as e:
            raise DataProcessingError(
                f"Failed to read data from project files: {str(e)}",
                {"project_id": project_id, "file_count": len(file_paths)},
            )

        for file_path in file_paths:
            # First, check if file already exists
            existing_file = db.exec(select(File).where(File.path == file_path)).first()

            if not existing_file:
                # Create new file record
                file_record = File(path=file_path)
                db.add(file_record)
                db.flush()
            else:
                file_record = existing_file

            # Create ProjectFile (the association with project-specific config)
            project_file = ProjectFile(
                project_id=project_id,
                file_id=file_record.id,
                file_type=Path(file_path).suffix.lower(),
                downsampling=1.0,
            )
            db.add(project_file)
            db.flush()

            # Create variables for this project-file combination
            if file_path in files_data:
                for var_name, var_config in files_data[file_path].items():
                    file_variable = FileVariable(
                        file_id=project_file.id,  # Links to ProjectFile, not File
                        var_name=var_name,
                        **var_config.model_dump(),
                    )
                    db.add(file_variable)

            # Create the many-to-many link
            project_file_link = ProjectFileLink(
                project_id=project_id, file_id=file_record.id
            )
            db.add(project_file_link)

    # def _create_project_files(
    #     self, db: SessionDep, project_id: int, file_paths: List[str]
    # ):
    #     """Create files and their variables from file paths"""
    #     if not file_paths:
    #         return
    #
    #     try:
    #         # Read data from files to discover variables
    #         files_data = data_processor.read_data(file_paths)
    #     except Exception as e:
    #         raise DataProcessingError(
    #             f"Failed to read data from project files: {str(e)}",
    #             {"project_id": project_id, "file_count": len(file_paths)},
    #         )
    #
    #     for file_path in file_paths:
    #         # Create file record
    #         project_file = ProjectFile(
    #             project_id=project_id,
    #             path=file_path,
    #             file_type=Path(file_path).suffix.lower(),
    #             downsampling=1.0,  # default
    #         )
    #         db.add(project_file)
    #         db.flush()
    #
    #         # Create variables for this file
    #         if file_path in files_data:
    #             for var_name, var_config in files_data[file_path].items():
    #                 file_variable = FileVariable(
    #                     file_id=project_file.id,
    #                     var_name=var_name,
    #                     **var_config.model_dump(),
    #                 )
    #                 db.add(file_variable)

    def _update_project_files(
        self, db: SessionDep, project_id: int, new_file_paths: List[str]
    ):
        """Update project files - remove old ones, add new ones"""
        # Get current ProjectFiles for this project
        current_project_files = db.exec(
            select(ProjectFile).where(ProjectFile.project_id == project_id)
        ).all()

        current_paths = set()
        for pf in current_project_files:
            current_paths.add(pf.file.path)

        new_paths = set(new_file_paths)

        # Remove files that are no longer needed
        paths_to_remove = current_paths - new_paths
        if paths_to_remove:
            for project_file in current_project_files:
                if project_file.file.path in paths_to_remove:
                    # Delete variables first
                    db.exec(
                        delete(FileVariable).where(
                            FileVariable.file_id == project_file.id
                        )
                    )
                    # Delete ProjectFileLink
                    db.exec(
                        delete(ProjectFileLink).where(
                            ProjectFileLink.project_id == project_id,
                            ProjectFileLink.file_id == project_file.file_id,
                        )
                    )
                    # Delete ProjectFile
                    db.delete(project_file)

        # Add new files
        paths_to_add = new_paths - current_paths
        if paths_to_add:
            self._create_project_files(db, project_id, list(paths_to_add))

    # def _update_project_files(
    #     self, db: SessionDep, project_id: int, new_file_paths: List[str]
    # ):
    #     """Update project files - remove old ones, add new ones"""
    #     # Get current file paths
    #     current_files = db.exec(
    #         select(ProjectFile).where(ProjectFile.project_id == project_id)
    #     ).all()
    #     current_paths = {f.path for f in current_files}
    #     new_paths = set(new_file_paths)
    #
    #     # Remove files that are no longer needed
    #     paths_to_remove = current_paths - new_paths
    #     if paths_to_remove:
    #         files_to_remove = [f for f in current_files if f.path in paths_to_remove]
    #         for file_record in files_to_remove:
    #             # Delete variables first
    #             db.exec(
    #                 delete(FileVariable).where(FileVariable.file_id == file_record.id)
    #             )
    #             db.delete(file_record)
    #
    #     # Add new files
    #     paths_to_add = new_paths - current_paths
    #     if paths_to_add:
    #         self._create_project_files(db, project_id, list(paths_to_add))

    def _build_project_read(self, db: SessionDep, project: Project) -> ProjectRead:
        """Build a complete ProjectRead with files and variables"""
        files_data = []

        # Get ProjectFiles instead of direct files
        project_files = db.exec(select(File).where(File.project_id == project.id)).all()

        for project_file in project_files:
            variables_data = []
            for variable in project_file.variables:
                variables_data.append(
                    FileVariableRead(
                        id=variable.id,
                        var_name=variable.var_name,
                        thr_min=variable.thr_min,
                        thr_min_sel=variable.thr_min_sel,
                        thr_max=variable.thr_max,
                        thr_max_sel=variable.thr_max_sel,
                        selected=variable.selected,
                        unit=variable.unit,
                        x_axis=variable.x_axis,
                        y_axis=variable.y_axis,
                        z_axis=variable.z_axis,
                    )
                )

            files_data.append(
                ProjectFileRead(
                    id=project_file.id,
                    path=project_file.file.path,  # Get path from related File
                    file_type=project_file.file_type,
                    downsampling=project_file.downsampling,
                    variables=variables_data,
                )
            )

        return ProjectRead(
            id=project.id,
            name=project.name,
            description=project.description,
            favourite=project.favourite,
            created=project.created,
            last_opened=project.last_opened,
            files=files_data,
        )

    # def _build_project_read(self, db: SessionDep, project: Project) -> ProjectRead:
    #     """Build a complete ProjectRead with files and variables"""
    #     files_data = []
    #
    #     for file_record in project.files:
    #         variables_data = []
    #         for variable in file_record.variables:
    #             variables_data.append(
    #                 FileVariableRead(
    #                     id=variable.id,
    #                     var_name=variable.var_name,
    #                     thr_min=variable.thr_min,
    #                     thr_min_sel=variable.thr_min_sel,
    #                     thr_max=variable.thr_max,
    #                     thr_max_sel=variable.thr_max_sel,
    #                     selected=variable.selected,
    #                     unit=variable.unit,
    #                     x_axis=variable.x_axis,
    #                     y_axis=variable.y_axis,
    #                     z_axis=variable.z_axis,
    #                 )
    #             )
    #
    #         files_data.append(
    #             ProjectFileRead(
    #                 id=file_record.id,
    #                 path=file_record.path,
    #                 file_type=file_record.file_type,
    #                 downsampling=file_record.downsampling,
    #                 variables=variables_data,
    #             )
    #         )
    #
    #     return ProjectRead(
    #         id=project.id,
    #         name=project.name,
    #         description=project.description,
    #         favourite=project.favourite,
    #         created=project.created,
    #         last_opened=project.last_opened,
    #         files=files_data,
    #     )


class CRUDProjectFile:
    def update_file(self, db: SessionDep, file_id: int, **kwargs) -> ProjectFile:
        """Update file-level configuration"""
        file_record = db.get(ProjectFile, file_id)
        if not file_record:
            raise ValueError(f"File {file_id} not found")

        for key, value in kwargs.items():
            if hasattr(file_record, key):
                setattr(file_record, key, value)

        db.add(file_record)
        db.commit()
        db.refresh(file_record)
        return file_record

    def update_variable(
        self, db: SessionDep, file_id: int, var_name: str, **kwargs
    ) -> FileVariable:
        """Update variable configuration for a specific file"""
        variable = db.exec(
            select(FileVariable).where(
                FileVariable.file_id == file_id, FileVariable.var_name == var_name
            )
        ).first()

        if not variable:
            raise ValueError(f"Variable {var_name} not found in file {file_id}")

        for key, value in kwargs.items():
            if hasattr(variable, key):
                setattr(variable, key, value)

        db.add(variable)
        db.commit()
        db.refresh(variable)
        return variable


class CRUDProcessJob:
    def create_process_job(self, db: SessionDep, project_id: int) -> ProcessJob:
        job = ProcessJob(project_id=project_id)
        db.add(job)
        db.commit()
        db.refresh(job)
        return job

    def update_process_job(self, db: SessionDep, job_id: int, **kwargs):
        job = db.exec(select(ProcessJob).where(ProcessJob.id == job_id)).first()
        for k, v in kwargs.items():
            setattr(job, k, v)
        job.updated_at = datetime.utcnow()
        db.add(job)
        db.commit()
        db.refresh(job)
        return job

    def get_process_job(self, db: SessionDep, job_id: int) -> ProcessJob:
        return db.exec(select(ProcessJob).where(ProcessJob.id == job_id)).first()


# Instances
crud_project = CRUDProject()
crud_project_file = CRUDProjectFile()
crud_process_job = CRUDProcessJob()
#
#
# class CRUDConfigRender:
#     def create_render(
#         self, db: SessionDep, config_create: ConfigRenderCreate
#     ) -> ConfigRenderRead:
#         config_process = db.exec(
#             select(ConfigProcess).where(
#                 ConfigProcess.project_id == config_create.project_id,
#                 ConfigProcess.var_name == config_create.var_name,
#             )
#         ).first()
#
#         if not config_process:
#             raise ConfigProcessNotFoundError(
#                 config_create.project_id, config_create.var_name
#             )
#
#         config_create.thr_min = config_process.thr_min
#         config_create.thr_min = config_process.thr_min
#         config_create.thr_max = config_process.thr_max
#
#         config = ConfigRender.model_validate(config_create)
#         db.add(config)
#         db.commit()
#         db.refresh(config)
#         return ConfigRenderRead.model_validate(config)
#
#
# crud_config_render = CRUDConfigRender()
