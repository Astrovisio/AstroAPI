import logging
import os
import random
from typing import Dict, List

import polars as pl
from sqlmodel import SQLModel

from api.models import ConfigProcessCreate, ConfigProcessRead, File
from src import gets, processors

logger = logging.getLogger(__name__)


class FileVariable(SQLModel):
    var_name: str
    thr_min: float
    thr_max: float
    selected: bool
    unit: str
    downsampling: float
    x_axis: bool
    y_axis: bool
    z_axis: bool

    def __init__(self):
        self.var_name = "variable_" + str(random.randint(1, 100))
        self.thr_min = random.uniform(0.0, 10.0)
        self.thr_max = random.uniform(10.0, 20.0)
        self.selected = random.choice([True, False])
        self.unit = random.choice(["K", "m/s", "Jy"])
        self.downsampling = random.uniform(0.1, 1.0)
        self.x_axis = random.choice([True, False])
        self.y_axis = random.choice([True, False])
        self.z_axis = random.choice([True, False])


class DataProcessor:
    @staticmethod
    def read_data(files: List[File]) -> Dict[str, Dict[str, ConfigProcessCreate]]:
        if os.getenv("API_TEST"):
            return DataProcessor.read_data_test(files)

        config_processes = {}
        for file in files:
            config_processes[file.path] = {}
            variables = gets.getThresholds(file.path)
            for key, value in variables.items():
                value.thr_min_sel = value.thr_min
                value.thr_max_sel = value.thr_max
                config_process = ConfigProcessCreate(
                    downsampling=1, var_name=key, **value.model_dump()
                )
                config_processes[file.path][key] = config_process
        return config_processes

    @staticmethod
    def read_data_test(files: List[File]) -> Dict[str, Dict[str, ConfigProcessCreate]]:
        config_processes = {}
        for file in files:
            config_processes[file.path] = {}
            for _ in range(random.randint(1, 3)):
                file_var = FileVariable()
                config_process = ConfigProcessCreate(**file_var.model_dump())
                config_processes[file.path][file_var.var_name] = config_process
        return config_processes

    @staticmethod
    def process_data(
        pid: int, paths: List[str], config: ConfigProcessRead, progress_callback=None
    ) -> str:
        combined_df = pl.DataFrame()
        for i, path in enumerate(paths):
            w = i / len(paths)

            def scaled_callback(progress):
                if progress_callback:
                    progress_callback(progress * w)

            df = processors.convertToDataframe(
                path, config, progress_callback=scaled_callback
            )
            if progress_callback:
                progress_callback(0.85 * w)
            combined_df = pl.concat([combined_df, df]).unique()
            if progress_callback:
                progress_callback(0.95 * w)
        return combined_df


data_processor = DataProcessor()
