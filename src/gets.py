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


def finite_min_max(series):
    data = series.to_numpy()
    data = data[np.isfinite(data)]
    return float(np.nanmin(data)), float(np.nanmax(data))


def getThresholds(file: FileCreate, family=None) -> Dict[str, VariableBase]:

    res = {}

    if getFileType(file.path) == "fits":

        cube = fits_to_dataframe(file)
        thr_min, thr_max = finite_min_max(cube["value"])

        for key in ("x", "y", "z", "value"):
            res[key] = VariableBase(
                var_name=key,
                thr_min=thr_min,
                thr_max=thr_max,
                unit=key,
            )

        del cube

    else:

        def compute_thresholds(sim):

            keys = ["x", "y", "z"] + sim.loadable_keys()
            keys.remove("pos")

            for key in keys:
                data = sim[key]
                if data.ndim > 1:
                    for i in range(data.shape[1]):
                        subarray = data[:, i]
                        subarray = subarray[np.isfinite(subarray)]
                        var_name = f"{key}-{i}"
                        res = VariableBase(
                            var_name=var_name,
                            thr_min=float(np.nanmin(subarray)),
                            thr_max=float(np.nanmax(subarray)),
                            unit=str(data.units),
                        )
                        yield var_name, res
                else:
                    subarray = data[np.isfinite(data)]
                    res = VariableBase(
                        var_name=key,
                        thr_min=float(np.nanmin(subarray)),
                        thr_max=float(np.nanmax(subarray)),
                        unit=str(data.units),
                    )
                    yield key, res

        with load_data(file.path) as sim:
            sim.physical_units()

            res = dict(compute_thresholds(sim))

        del sim

    gc.collect()

    return res
