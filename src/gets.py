import gc
from typing import Dict, List

import numpy as np

from api.models import HistoBase, VariableBase
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


def get_file_stats(file: str, nbins: int = 50) -> Dict[str, object]:
    def build_bins(counts: np.ndarray, edges: np.ndarray) -> List[HistoBase]:
        if counts is None and edges is None:
            return []
        bins: List[HistoBase] = []
        for i in range(len(counts)):
            bins.append(
                HistoBase(
                    bin_index=int(i),
                    bin_min=float(edges[i]),
                    bin_max=float(edges[i + 1]),
                    count=int(counts[i]),
                )
            )
        return bins

    thresholds: Dict[str, VariableBase] = {}
    histograms: Dict[str, List[HistoBase]] = {}
    total_points = 0

    if getFileType(file) == "fits":
        cube = fits_to_dataframe(file)
        total_points = cube.shape[0]
        thr_min, thr_max = finite_min_max(cube["value"])
        for key in ("x", "y", "z", "value"):
            thresholds[key] = VariableBase(
                var_name=key,
                thr_min=thr_min,
                thr_max=thr_max,
                unit=key,
            )
        for key, var in thresholds.items():
            if key not in cube.columns:
                continue
            data = cube[key].to_numpy()
            data = data[np.isfinite(data)]
            try:
                counts, edges = np.histogram(
                    data, bins=nbins, range=(var.thr_min, var.thr_max)
                )
            except ValueError:
                counts, edges = None, None
            histograms[key] = build_bins(counts, edges)
        del cube
    else:
        with load_data(file) as sim:
            sim.physical_units()
            total_points = len(sim)

            keys = ["x", "y", "z"] + sim.loadable_keys()
            keys.remove("pos")

            for key in keys:
                data = sim[key]
                if getattr(data, "ndim", 1) > 1:
                    for i in range(data.shape[1]):
                        subarray = data[:, i]
                        subarray = subarray[np.isfinite(subarray)]
                        var_name = f"{key}-{i}"

                        thr_min = float(np.nanmin(subarray))
                        thr_max = float(np.nanmax(subarray))
                        thresholds[var_name] = VariableBase(
                            var_name=var_name,
                            thr_min=thr_min,
                            thr_max=thr_max,
                            unit=str(data.units),
                        )

                        try:
                            counts, edges = np.histogram(
                                subarray, bins=nbins, range=(thr_min, thr_max)
                            )
                        except ValueError:
                            # handle the case where all values are identical
                            counts, edges = None, None
                        histograms[var_name] = build_bins(counts, edges)
                else:
                    arr = data[np.isfinite(data)]

                    thr_min = float(np.nanmin(arr))
                    thr_max = float(np.nanmax(arr))
                    thresholds[key] = VariableBase(
                        var_name=key,
                        thr_min=thr_min,
                        thr_max=thr_max,
                        unit=str(data.units),
                    )

                    try:
                        counts, edges = np.histogram(
                            arr, bins=nbins, range=(thr_min, thr_max)
                        )
                    except ValueError:
                        # handle the case where all values are identical
                        counts, edges = None, None
                    histograms[key] = build_bins(counts, edges)
            del sim

    gc.collect()
    return {
        "total_points": total_points,
        "thresholds": thresholds,
        "histograms": histograms,
    }
