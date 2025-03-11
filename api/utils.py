from typing import List
from src import gets
from api.models import ConfigProcessCreate, File


def read_data(files: List[File]) -> List[ConfigProcessCreate]:
    config_processes = []
    for file in files:
        variables = gets.getThresholds(file.path)
        for key, value in variables.items():
            config_process = ConfigProcessCreate(
                downsampling=1, var_name=key, **value.model_dump()
            )
            config_processes.append(config_process)
    return config_processes
