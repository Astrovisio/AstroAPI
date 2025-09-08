import logging
import os
import random
from typing import Dict, List

import polars as pl
from sqlmodel import SQLModel

from api.models import FileCreate, VariableBase
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
        if os.getenv("API_TEST"):
            return DataProcessor.read_data_test(file_paths)

        mapping_files = {}
        for file_path in file_paths:
            file_type = "hdf5" if file_path.endswith(".hdf5") else "fits"
            file = FileCreate(file_type=file_type, file_path=file_path)
            variables = gets.getThresholds(file_path)
            print(f"Extracted variables: {variables}", flush=True)
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

    # @staticmethod
    # def process_data(
    #     pid: int, paths: List[str], config: ConfigProcessRead, progress_callback=None
    # ) -> str:
    #     combined_df = pl.DataFrame()
    #     for i, path in enumerate(paths):
    #         w = i / len(paths)
    #
    #         def scaled_callback(progress):
    #             if progress_callback:
    #                 progress_callback(progress * w * 0.8)
    #
    #         df = processors.convertToDataframe(
    #             path, config, progress_callback=scaled_callback
    #         )
    #         if progress_callback:
    #             progress_callback(0.85 * w)
    #         combined_df = pl.concat([combined_df, df]).unique()
    #         if progress_callback:
    #             progress_callback(0.95 * w)
    #     return combined_df


data_processor = DataProcessor()
