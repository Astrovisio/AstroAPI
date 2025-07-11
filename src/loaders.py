import pynbody
from astropy.io import fits

from src.utils import getFileType


def loadSimulation(path: str, family=None) -> pynbody.snapshot.SimSnap:

    if family is None:
        sim = pynbody.load(path)
        sim = getattr(sim, str(sim.families()[0]))

    else:
        sim = getattr(pynbody.load(path), family)

    return sim


def loadObservation(path: str) -> fits.hdu.image.PrimaryHDU:

    obs = fits.open(path)

    return obs


def load(path: str):

    if getFileType(path) == "fits":
        return loadObservation(path)

    else:
        return loadSimulation(path)
