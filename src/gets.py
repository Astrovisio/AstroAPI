import gc
from typing import Dict, List

import numpy as np

from api.models import FileCreate, VariableBase
from src.loaders import load_data
from src.processors import fits_to_dataframe
from src.utils import getFileType


def getSimFamily(path: str) -> List[str]:

    with load_data(path) as sim:
        families = [str(el) for el in sim.families()]

    return families


def getKeys(path: str, family=None) -> list:

    if getFileType(path) == "fits":
        return ["x", "y", "z", "value"]

    else:
        with load_data(path) as sim:
            keys = sim.loadable_keys()

        del sim
        gc.collect()

        return keys


def getThresholds(file: FileCreate, family=None) -> Dict[str, VariableBase]:

    res = {}

    if getFileType(file.file_path) == "fits":

        cube = fits_to_dataframe(file)

        res["x"] = VariableBase(
            var_name="x",
            thr_min=float(cube["x"].min()),
            thr_max=float(cube["x"].max()),
            unit="x",
        )
        res["y"] = VariableBase(
            var_name="y",
            thr_min=float(cube["y"].min()),
            thr_max=float(cube["y"].max()),
            unit="y",
        )
        res["z"] = VariableBase(
            var_name="z",
            thr_min=float(cube["z"].min()),
            thr_max=float(cube["z"].max()),
            unit="z",
        )
        res["value"] = VariableBase(
            var_name="value",
            thr_min=float(cube["value"].min()),
            thr_max=float(cube["value"].max()),
            unit="value",
        )

        del cube

    else:

        def compute_thresholds(sim):

            keys = ["x", "y", "z"] + sim.loadable_keys()
            keys.remove("pos")

            for key in keys:
                if sim[key].ndim > 1:
                    for i in range(sim[key].shape[1]):
                        var_name = f"{key}-{i}"
                        res = VariableBase(
                            var_name=var_name,
                            thr_min=float(sim[key][:, i].min()),
                            thr_max=float(sim[key][:, i].max()),
                            unit=str(sim[key].units),
                        )
                        yield var_name, res
                else:
                    res = VariableBase(
                        var_name=key,
                        thr_min=float(sim[key].min()),
                        thr_max=float(sim[key].max()),
                        unit=str(sim[key].units),
                    )
                    yield key, res

        with load_data(file.file_path) as sim:
            sim.physical_units()

            res = dict(compute_thresholds(sim))

        del sim

    gc.collect()

    return res
