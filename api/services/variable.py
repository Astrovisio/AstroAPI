from typing import List

from sqlmodel import Session, select

from api.error_handlers import FileNotFoundError
from api.models import (
    File,
    FileUpdate,
    ProjectFileVariableConfig,
    Variable,
    VariableRead,
)


class VariableService:
    """API-tied service for per-variable configuration and views.

    Purpose:
    - Provide CRUD operations for per-project variable configs consumed by API routes.

    Responsibilities:
    - Build VariableRead by combining Variable with ProjectFileVariableConfig.
    - Read/update variable thresholds, selection, axes, etc., for a project-file pair.
    - Fetch configs in bulk for a project-file pair and apply sane defaults.
    """

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
