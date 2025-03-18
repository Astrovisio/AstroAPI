from typing import Dict, List
import pandas as pd
from src import gets, processors
from api.models import ConfigProcessCreate, ConfigProcessRead, File


def read_data(files: List[File]) -> Dict[str, Dict[str, ConfigProcessCreate]]:
    config_processes = {}
    for file in files:
        config_processes[file.path] = {}
        variables = gets.getThresholds(file.path)
        for key, value in variables.items():
            config_process = ConfigProcessCreate(
                downsampling=1, var_name=key, **value.model_dump()
            )
            config_processes[file.path][key] = config_process
    return config_processes


def process_data(paths: List[str], config: ConfigProcessRead) -> str:
    combined_df = pd.DataFrame()
    for path in paths:
        df = processors.convertToDataframe(path, config)
        combined_df = pd.concat([combined_df, df], ignore_index=True).drop_duplicates()
    new_path = "./data/processed.csv"
    combined_df.to_csv(new_path, index=False)
    return new_path
