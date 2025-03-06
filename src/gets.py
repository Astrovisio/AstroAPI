import pynbody
from src.loaders import loadSimulation, loadObservation
from src.utils import getFileType
from api.models import ConfigProcessCreate
from spectral_cube import SpectralCube
from typing import List

def getKeys(path:str) -> list:
    
    if getFileType(path)=="fits":
        return ["x", "y", "vel"]
    
    else:
        sim = loadSimulation(path)
        keys = sim.loadable_keys()
        keys = ["x", "y", "z"]+keys
        del sim
        
        return keys
    
def getThresholds(path:str) -> List[ConfigProcessCreate]:
    
    if getFileType(path)=="fits":
             
        res = []
        cube = loadObservation(path)
        velo, dec, ra = cube.world[:]  
        
      
        res.append(ConfigProcessCreate(thr_min = float(ra.min().value),
                            thr_max = float(ra.max().value),
                            unit = "rad",
                            var_name = "x"))
        res.append(ConfigProcessCreate(thr_min = float(dec.min().value),
                            thr_max = float(dec.max().value),
                            unit = "rad",
                            var_name = "y"))
        res.append(ConfigProcessCreate(thr_min = float(velo.min().value),
                            thr_max = float(velo.max().value),
                            unit = "m/s",
                            var_name = "v"))
        
        del cube
        
        return res
    
    else:        
        sim = loadSimulation(path)
        res = []        
        
        for key in sim.loadable_keys():
            try:
                res.append(res.append(ConfigProcessCreate(thr_min = float(sim[key].min())),
                            thr_max = float(sim[key].max(),
                            unit = str(sim[key].units),
                            var_name = key)))
                
            except(KeyError, pynbody.units.UnitsException):
                pass
            
        del sim
        
        return res