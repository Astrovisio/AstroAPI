import pynbody
from spectral_cube import SpectralCube

from src.utils import getFileType


def loadSimulation(path: str, family=None) -> pynbody.snapshot.SimSnap:

    if family is None:
        sim = pynbody.load(path)
        sim = getattr(sim, str(sim.families()[0]))

    else:
        sim = getattr(pynbody.load(path), family)

    return sim


def loadObservation(path: str) -> SpectralCube:

    obs = SpectralCube.read(path)

    return obs


def load(path: str):

    if getFileType(path) == "fits":
        return loadObservation(path)

    else:
        return loadSimulation(path)
