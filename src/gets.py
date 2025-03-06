import pynbody
from .loaders import loadSimulation, loadObservation
from .utils import getFileType
from spectral_cube import SpectralCube

def getKeys(path:str) -> list:
    
    if getFileType(path)=="fits":
        return ["x", "y", "vel"]
    
    else:
        sim = loadSimulation(path)
        keys = sim.loadable_keys()
        keys = ["x", "y", "z"]+keys
        del sim
        
        return keys
    
def getThresholds(path:str) -> dict:
    
    if getFileType(path)=="fits":
        
        cube = loadObservation(path)
        velo, dec, ra = cube.world[:]  
        
        thresholds = {
            "x_min": float(ra.min().value),
            "x_max": float(ra.max().value),
            "y_min": float(dec.min().value),
            "y_max": float(dec.max().value),
            "v_min": float(velo.min().value),
            "v_max": float(velo.max().value)
        }
        
        del cube
        
        return thresholds
    
    else:        
        sim = loadSimulation(path)
        res = {}        
        
        for key in sim.loadable_keys():
            try:
                res[f"{key}_min"], res[f"{key}_max"]  = float(sim[key].min()), float(sim[key].max())
            except(KeyError, pynbody.units.UnitsException):
                pass
            
        del sim
        
        return res