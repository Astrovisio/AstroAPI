import pynbody
from src.loaders import loadSimulation, loadObservation
from src.utils import getFileType
from api.models import VariableConfig, VariableConfigRead
from spectral_cube import SpectralCube
from typing import List, Dict
import numpy as np


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
        keys = ["x", "y", "z"] + keys
        del sim

        return keys


def getThresholds(path: str, family=None) -> Dict[str, VariableConfigRead]:

    res = {}

    if getFileType(path) == "fits":

        cube = loadObservation(path)
        velo, dec, ra = cube.world[:, :, :]

        res["ra"] = VariableConfig(
            thr_min=float(ra.min().value),
            thr_max=float(ra.max().value),
            unit=str(ra.unit),
        )
        res["dec"] = VariableConfig(
            thr_min=float(dec.min().value),
            thr_max=float(dec.max().value),
            unit=str(dec.unit),
        )
        res["velocity"] = VariableConfig(
            thr_min=float(velo.min().value),
            thr_max=float(velo.max().value),
            unit=str(velo.unit),
        )
        res["intensity"] = VariableConfig(
            thr_min=float(np.nanmin(cube.unmasked_data[:].value)),
            thr_max=float(np.nanmax(cube.unmasked_data[:].value)),
            unit=str(cube.unmasked_data[:].unit),
        )

        del cube

    else:
        sim = loadSimulation(path, family)
        sim.physical_units()

        for key in ["x", "y", "z"] + sim.loadable_keys():
            res[key] = VariableConfigRead(
                thr_min=float(sim[key].min()),
                thr_max=float(sim[key].max()),
                unit=str(sim[key].units),
            )

        del sim

    return res
