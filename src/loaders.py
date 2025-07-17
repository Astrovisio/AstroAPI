from contextlib import contextmanager

import pynbody
from astropy.io import fits

from src.utils import getFileType


@contextmanager
def load_data(path: str, family=None):
    filetype = getFileType(path)
    if filetype == "fits":
        obs = fits.open(path)
        try:
            yield obs
        finally:
            obs.close()
    else:
        if family is None:
            sim = pynbody.load(path)
            sim = getattr(sim, str(sim.families()[0]))
        else:
            sim = getattr(pynbody.load(path), family)
        yield sim
