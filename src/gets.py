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
        return ["ra", "dec", "velocity", "intensity"]

    else:
        sim = loadSimulation(path, family)
        keys = sim.loadable_keys()
        del sim

        return keys


def getThresholds(path: str, family=None) -> Dict[str, VariableConfigRead]:

    res = {}

    if getFileType(path) == "fits":

        cube = fits_to_dataframe(path)

        res["ra"] = VariableConfig(
            thr_min=float(cube["ra"].min()),
            thr_max=float(cube["ra"].max()),
            unit="deg",
        )
        res["dec"] = VariableConfig(
            thr_min=float(cube["dec"].min()),
            thr_max=float(cube["dec"].max()),
            unit="deg",
        )
        res["velocity"] = VariableConfig(
            thr_min=float(cube["velocity"].min()),
            thr_max=float(cube["velocity"].max()),
            unit="m / s",
        )
        res["intensity"] = VariableConfig(
            thr_min=float(cube["intensity"].min()),
            thr_max=float(cube["intensity"].max()),
            unit="K",
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
