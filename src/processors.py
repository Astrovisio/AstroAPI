import numpy as np
import pandas as pd

from api.models import ConfigProcessRead
from src.loaders import loadObservation, loadSimulation
from src.utils import getFileType


def fits_to_dataframe(path, config: ConfigProcessRead = None, progress_callback=None):

    # Load the spectral cube
    cube = loadObservation(path)

    df_list = []
    n_slices = cube.shape[0]

    # Iterate over the spectral axis (velocity axis)
    for i in range(n_slices):
        # Slice one spectral frame at a time
        slab = cube[i, :, :]  # shape: (y, x)

        # Get world coordinates for this frame
        world = slab.wcs.pixel_to_world_values(
            *np.meshgrid(
                np.arange(cube.shape[2]),  # x (RA)
                np.arange(cube.shape[1]),  # y (Dec)
                indexing="xy",
            )
        )

        ra = world[0].flatten()
        dec = world[1].flatten()
        velo = cube.spectral_axis[i].value  # Single velocity value for this slice
        intensity = slab.filled_data[:].value.flatten()

        # Build DataFrame for this slab
        df_slice = pd.DataFrame(
            {"velocity": velo, "ra": ra, "dec": dec, "intensity": intensity}
        )

        df_list.append(df_slice)
        if progress_callback:
            progress_callback(i / n_slices * 0.8)  # up to 80% for reading

    # Concatenate all slices into a single DataFrame
    df = pd.concat(df_list, ignore_index=True)
    df.dropna(inplace=True)
    del cube
    if not config:
        return df
    df_sampled = df.sample(frac=config.downsampling)
    if progress_callback:
        progress_callback(0.9)

    return df_sampled


def pynbody_to_dataframe(
    path, config: ConfigProcessRead, family=None, progress_callback=None
):

    sim = loadSimulation(path, family)

    sim.physical_units()

    data = {}

    n_vars = len([v for v in config.variables.values() if v.selected])
    var_idx = 0

    for key, value in config.variables.items():
        if value.selected:
            if "-" in key:
                key, i = key.split("-")
                data[f"{key}-{i}"] = sim[key][:, int(i)].astype(float)

            else:
                data[key] = sim[key].astype(float)
            var_idx += 1
            if progress_callback and n_vars > 0:
                progress_callback(var_idx / n_vars * 0.4)  # up to 80% for reading

    df = pd.DataFrame(data)

    df_sampled = df.sample(frac=config.downsampling)
    if progress_callback:
        progress_callback(0.45)

    del sim
    if progress_callback:
        progress_callback(0.5)

    return df_sampled


def filter_dataframe(
    df: pd.DataFrame, config: ConfigProcessRead, progress_callback=None
) -> pd.DataFrame:
    filtered_df = df.copy()

    for var_name, var_config in config.variables.items():

        if var_config.selected:
            if var_name in ["x", "y", "z"]:
                # Filter the DataFrame based on the specified thresholds
                filtered_df = filtered_df[
                    (filtered_df[var_name] >= var_config.thr_min_sel)
                    & (filtered_df[var_name] <= var_config.thr_max_sel)
                ]
                if progress_callback:
                    progress_callback(
                        0.5
                        + 0.4
                        * list(config.variables.keys()).index(var_name)
                        / len(config.variables)
                    )
            else:
                filtered_df.loc[
                    (filtered_df[var_name] < var_config.thr_min_sel)
                    | (filtered_df[var_name] > var_config.thr_max_sel),
                    var_name,
                ] = 0
                if progress_callback:
                    progress_callback(
                        0.5
                        + 0.4
                        * list(config.variables.keys()).index(var_name)
                        / len(config.variables)
                    )

    return filtered_df


def convertToDataframe(
    path, config: ConfigProcessRead, family=None, progress_callback=None
) -> pd.DataFrame:  # Maybe needs a better name

    if getFileType(path) == "fits":
        df = fits_to_dataframe(
            path, config, progress_callback=progress_callback
        )  # When we load an observation since the available data will always be just "x,y,z,intensity" it's meaningless to drop unused axes, we always need all 4

    else:
        df = pynbody_to_dataframe(path, config, family, progress_callback)

    return filter_dataframe(df, config, progress_callback)
