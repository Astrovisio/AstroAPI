import logging
import os
import random
from typing import Dict, List, Tuple

import polars as pl
from sqlmodel import SQLModel

from api.models import FileCreate, FileRead, HistoBase, VariableBase
from src import gets, processors

logger = logging.getLogger(__name__)


class TestVariable(SQLModel):
    var_name: str
    thr_min: float
    thr_max: float
    selected: bool
    unit: str
    x_axis: bool
    y_axis: bool
    z_axis: bool

    def __init__(self):
        self.var_name = "variable_" + str(random.randint(1, 100))
        self.thr_min = random.uniform(0.0, 10.0)
        self.thr_max = random.uniform(10.0, 20.0)
        self.selected = random.choice([True, False])
        self.unit = random.choice(["K", "m/s", "Jy"])
        self.x_axis = random.choice([True, False])
        self.y_axis = random.choice([True, False])
        self.z_axis = random.choice([True, False])


class DataProcessor:

    @staticmethod
    def read_data(
        file_paths: List[str],
    ) -> Tuple[Dict[str, FileCreate], Dict[str, Dict[str, List[HistoBase]]]]:
        """
        Reads data from given file paths and extracts variables with their thresholds.
        Returns a mapping of file paths to FileCreate objects containing variable info.
        """
        if os.getenv("API_TEST"):
            return DataProcessor.read_data_test(file_paths)

        mapping_files = {}
        mapping_histos = {}
        for file_path in file_paths:
            file_type = "hdf5" if file_path.endswith(".hdf5") else "fits"
            file_name = os.path.basename(file_path).rsplit(".", 1)[0]
            file_size = os.path.getsize(file_path)
            file = FileCreate(
                type=file_type, name=file_name, path=file_path, size=file_size
            )
            file_stats = gets.get_file_stats(file_path)
            variables = file_stats["thresholds"]
            file.total_points = file_stats["total_points"]
            histos = file_stats["histograms"]
            for key, value in variables.items():
                value.thr_min_sel = value.thr_min
                value.thr_max_sel = value.thr_max
                variable = VariableBase(**value.model_dump())
                file.variables.append(variable)
            mapping_files[file.path] = file
            mapping_histos[file.path] = histos
        return mapping_files, mapping_histos

    @staticmethod
    def read_data_test(
        file_paths: List[str],
    ) -> Tuple[Dict[str, FileCreate], Dict[str, Dict[str, List[HistoBase]]]]:
        mapping_files: Dict[str, FileCreate] = {}
        mapping_histos: Dict[str, Dict[str, List[HistoBase]]] = {}

        for file_path in file_paths:
            file_name = os.path.basename(file_path).rsplit(".", 1)[0]
            file = FileCreate(type="hdf5", name=file_name, path=file_path, size=1)
            file.total_points = random.randint(100, 10_000)

            file_histos: Dict[str, List[HistoBase]] = {}
            for _ in range(random.randint(1, 3)):
                file_var = TestVariable()
                var_payload = file_var.model_dump()
                var_payload["thr_min_sel"] = file_var.thr_min
                var_payload["thr_max_sel"] = file_var.thr_max
                variable = VariableBase(**var_payload)
                file.variables.append(variable)

                # Create an empty histogram list placeholder for this variable
                file_histos[variable.var_name] = []

            mapping_files[file.path] = file
            mapping_histos[file.path] = file_histos

        return mapping_files, mapping_histos

    @staticmethod
    def process_data(file_config: FileRead, progress_callback=None) -> str:
        combined_df = pl.DataFrame()

        def scaled_callback(progress):
            if progress_callback:
                progress_callback(progress * 0.8)

        df = processors.convertToDataframe()
        if progress_callback:
            progress_callback(0.85)
        combined_df = pl.concat([combined_df, df]).unique()
        if progress_callback:
            progress_callback(0.95)
        return combined_df


data_processor = DataProcessor()
