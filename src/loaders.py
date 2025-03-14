import pynbody
from spectral_cube import SpectralCube
from src.utils import getFileType


def loadSimulation(path: str) -> pynbody.snapshot.SimSnap:

    sim = pynbody.load(path)

    return sim


def loadObservation(path: str) -> SpectralCube:

    obs = SpectralCube.read(path)

    return obs


def load(path: str):

    if getFileType(path) == "fits":
        return loadObservation(path)

    else:
        return loadSimulation(path)

