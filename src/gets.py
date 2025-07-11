from typing import Dict, List

import numpy as np

from api.models import VariableConfig, VariableConfigRead
from src.loaders import loadObservation, loadSimulation
from src.processors import fits_to_dataframe
from src.utils import getFileType


def getSimFamily(path: str) -> List[str]:

    sim = loadSimulation(path)
    families = [str(el) for el in sim.families()]

    return families


def getKeys(path: str, family=None) -> list:

    if getFileType(path) == "fits":
        return ["x", "y", "z", "value"]

    else:
        sim = loadSimulation(path, family)
        keys = sim.loadable_keys()
        del sim

        return keys


def getThresholds(path: str, family=None) -> Dict[str, VariableConfigRead]:

    res = {}

    if getFileType(path) == "fits":

        cube = fits_to_dataframe(path)
        
        
        res["x"] = VariableConfig(
            thr_min=float(cube["x"].min()),
            thr_max=float(cube["x"].max()),
            unit="x",
        )
        res["y"] = VariableConfig(
            thr_min=float(cube["y"].min()),
            thr_max=float(cube["y"].max()),
            unit="y",
        )
        res["z"] = VariableConfig(
            thr_min=float(cube["z"].min()),
            thr_max=float(cube["z"].max()),
            unit="z",
        )
        res["value"] = VariableConfig(
            thr_min=float(cube["value"].min()),
            thr_max=float(cube["value"].max()),
            unit="value",
        )


        del cube

    else:
        sim = loadSimulation(path, family)
        sim.physical_units()

        keys = ["x", "y", "z"] + sim.loadable_keys()
        keys.remove("pos")

        for key in keys:
            if sim[key].ndim > 1:
                for i in range(sim[key].shape[1]):
                    res[f"{key}-{i}"] = VariableConfigRead(
                        thr_min=float(sim[key][:, i].min()),
                        thr_max=float(sim[key][:, i].max()),
                        unit=str(sim[key].units),
                    )
            else:
                res[key] = VariableConfigRead(
                    thr_min=float(sim[key].min()),
                    thr_max=float(sim[key].max()),
                    unit=str(sim[key].units),
                )

        del sim

    return res
