from sqlmodel import SQLModel
from typing import List
import random
from api.models import ConfigProcessCreate


class FileVariable(SQLModel):
    var_name: str
    thr_min: float
    thr_max: float
    selected: bool
    downsampling: float
    x_axis: bool
    y_axis: bool
    z_axis: bool

    def __init__(self):
        self.var_name = "variable_" + str(random.randint(1, 100))
        self.thr_min = random.uniform(0.0, 10.0)
        self.thr_max = random.uniform(10.0, 20.0)
        self.selected = random.choice([True, False])
        self.downsampling = random.uniform(0.1, 1.0)
        self.x_axis = random.choice([True, False])
        self.y_axis = random.choice([True, False])
        self.z_axis = random.choice([True, False])


def read_data(files: List[str]) -> List[ConfigProcessCreate]:
    print(f"Faking reading data from {files}")
    config_processes = []
    for file in files:
        for var in range(random.randint(1, 3)):
            file_var = FileVariable()
            config_process = ConfigProcessCreate(
                var_name=file_var.var_name,
                thr_min=file_var.thr_min,
                thr_max=file_var.thr_max,
                selected=file_var.selected,
                downsampling=file_var.downsampling,
                x_axis=file_var.x_axis,
                y_axis=file_var.y_axis,
                z_axis=file_var.z_axis,
            )
            config_processes.append(config_process)
    return config_processes
