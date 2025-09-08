from typing import Dict, List, Optional

from sqlalchemy.orm import selectinload
from sqlmodel import Session, select

from api.models import (
    File,
    FileCreate,
    FileProjectLink,
    FileRead,
    Project,
    ProjectCreate,
    ProjectRead,
    ProjectUpdate,
    Variable,
    VariableRead,
)


class ProjectService:
    def __init__(self, session: Session):
        self.session = session

    def create_project(
        self, project_data: ProjectCreate, file_variables_map: Dict[str, FileCreate]
    ) -> ProjectRead:
        """
        Create a project with files and their variables in one transaction.

        Args:
            project_data: ProjectCreate payload from client
            file_variables_map: Dict mapping file_path -> list of variables data
        """
        # Create the project
        db_project = Project(
            name=project_data.name,
            favourite=project_data.favourite,
            description=project_data.description,
        )
        self.session.add(db_project)
        self.session.flush()  # Get the project ID without committing

        # Create files and variables
        for file_path in project_data.file_paths:
            # Determine file type from extension
            file_type = "hdf5" if file_path.endswith(".hdf5") else "fits"

            # Create file
            db_file = File(
                file_type=file_type,
                file_path=file_path,
            )
            self.session.add(db_file)
            self.session.flush()  # Get the file ID

            # Create variables for this file
            for var_data in file_variables_map[file_path].variables:
                db_variable = Variable(
                    **var_data.model_dump(),
                    file_id=db_file.id,
                    # Set other fields from var_data as needed
                )
                self.session.add(db_variable)

            # Link file to project
            link = FileProjectLink(project_id=db_project.id, file_id=db_file.id)
            self.session.add(link)

        self.session.commit()
        self.session.refresh(db_project)

        # Return with loaded relationships
        return self.get_project(db_project.id)

    def get_project(self, project_id: int) -> ProjectRead:
        """Get project with all files and variables loaded."""
        statement = (
            select(Project)
            .options(selectinload(Project.files).selectinload(File.variables))
            .where(Project.id == project_id)
        )
        project = self.session.exec(statement).first()
        print(f"Loaded project: {project}", flush=True)
        return ProjectRead.model_validate(project) if project else None

    def get_projects(self) -> List[ProjectRead]:
        """Get all projects with files and variables loaded."""
        statement = select(Project).options(
            selectinload(Project.files).selectinload(File.variables)
        )
        projects = self.session.exec(statement).all()
        return [ProjectRead.model_validate(p) for p in projects]

    def update_project(
        self, project_id: int, project_update: ProjectUpdate
    ) -> Optional[ProjectRead]:
        """Update project and optionally its files/variables."""
        db_project = self.session.get(Project, project_id)
        if not db_project:
            return None

        # Update project fields
        for field, value in project_update.model_dump(exclude_unset=True).items():
            if field not in ["file_paths", "files"]:
                setattr(db_project, field, value)

        # Handle file updates
        if project_update.files:
            for file_update in project_update.files:
                # Find existing file or create new one
                db_file = self.session.exec(
                    select(File).where(File.file_path == file_update.file_path)
                ).first()

                if db_file:
                    # Update existing file
                    for field, value in file_update.model_dump(
                        exclude=["variables"]
                    ).items():
                        setattr(db_file, field, value)

                    # Update variables
                    for var_update in file_update.variables:
                        db_var = self.session.exec(
                            select(Variable).where(
                                Variable.file_id == db_file.id,
                                Variable.var_name == var_update.var_name,
                            )
                        ).first()

                        if db_var:
                            for field, value in var_update.model_dump().items():
                                setattr(db_var, field, value)

        self.session.commit()
        return self.get_project_with_relations(project_id)

    def delete_project(self, project_id: int) -> bool:
        """Delete project and handle cascading deletes."""
        db_project = self.session.get(Project, project_id)
        if not db_project:
            return False

        # SQLModel/SQLAlchemy will handle cascade deletes based on your relationship setup
        self.session.delete(db_project)
        self.session.commit()
        return True

    def list_projects(self, skip: int = 0, limit: int = 100) -> List[ProjectRead]:
        """List projects with pagination."""
        statement = (
            select(Project)
            .options(selectinload(Project.files).selectinload(File.variables))
            .offset(skip)
            .limit(limit)
        )
        projects = self.session.exec(statement).all()
        return [ProjectRead.model_validate(p) for p in projects]


class FileService:
    def __init__(self, session: Session):
        self.session = session

    def update_file_processing_status(
        self, file_id: int, processed: bool
    ) -> Optional[FileRead]:
        """Update file processing status."""
        db_file = self.session.get(File, file_id)
        if not db_file:
            return None

        db_file.processed = processed
        self.session.commit()
        self.session.refresh(db_file)
        return FileRead.model_validate(db_file)


class VariableService:
    def __init__(self, session: Session):
        self.session = session

    def update_variable_selection(
        self, variable_id: int, selected: bool, **kwargs
    ) -> Optional[VariableRead]:
        """Update variable selection and other properties."""
        db_variable = self.session.get(Variable, variable_id)
        if not db_variable:
            return None

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

        self.session.commit()
        return [VariableRead.model_validate(var) for var in updated_vars]
