import logging
import os
import random
from typing import Dict, List

import polars as pl
from sqlmodel import SQLModel

from api.models import FileCreate, FileRead, VariableBase
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
    def read_data(file_paths: List[str]) -> Dict[str, FileCreate]:
        """
        Reads data from given file paths and extracts variables with their thresholds.
        Returns a mapping of file paths to FileCreate objects containing variable info.
        """
        if os.getenv("API_TEST"):
            return DataProcessor.read_data_test(file_paths)

        mapping_files = {}
        for file_path in file_paths:
            file_type = "hdf5" if file_path.endswith(".hdf5") else "fits"
            file = FileCreate(file_type=file_type, file_path=file_path)
            variables = gets.getThresholds(file)
            for key, value in variables.items():
                value.thr_min_sel = value.thr_min
                value.thr_max_sel = value.thr_max
                variable = VariableBase(**value.model_dump())
                file.variables.append(variable)
            mapping_files[file.file_path] = file
        return mapping_files

    @staticmethod
    def read_data_test(file_paths: List[str]) -> Dict[str, FileCreate]:
        mapping_files = {}
        for file_path in file_paths:
            file = FileCreate(file_type="hdf5", file_path=file_path)
            for _ in range(random.randint(1, 3)):
                file_var = TestVariable()
                variable = VariableBase(**file_var.model_dump())
                file.variables.append(variable)
            mapping_files[file.file_path] = file
        return mapping_files

    @staticmethod
    def process_data(file_config: FileRead, progress_callback=None) -> str:
        combined_df = pl.DataFrame()

        def scaled_callback(progress):
            if progress_callback:
                progress_callback(progress * 0.8)

        df = processors.convertToDataframe(
            file=file_config, progress_callback=scaled_callback
        )
        if progress_callback:
            progress_callback(0.85)
        combined_df = pl.concat([combined_df, df]).unique()
        if progress_callback:
            progress_callback(0.95)
        return combined_df


data_processor = DataProcessor()
