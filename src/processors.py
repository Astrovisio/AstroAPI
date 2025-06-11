import numpy as np
import pandas as pd

from api.models import ConfigProcessRead
from src.loaders import loadObservation, loadSimulation
from src.utils import getFileType


def fits_to_dataframe(path, config: ConfigProcessRead = None):

    # Load the spectral cube
    cube = loadObservation(path)

    df_list = []

    # Iterate over the spectral axis (velocity axis)
    for i in range(cube.shape[0]):
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

    # Concatenate all slices into a single DataFrame
    df = pd.concat(df_list, ignore_index=True)
    df.dropna(inplace=True)
    del cube
    if not config:
        return df
    df_sampled = df.sample(frac=config.downsampling)

    return df_sampled


def pynbody_to_dataframe(path, config: ConfigProcessRead, family=None):

    sim = loadSimulation(path, family)

    sim.physical_units()

    data = {}

    for key, value in config.variables.items():
        if value.selected:
            if "-" in key:
                key, i = key.split("-")
                data[f"{key}-{i}"] = sim[key][:, int(i)].astype(float)

            else:
                data[key] = sim[key].astype(float)

    df = pd.DataFrame(data)

    df_sampled = df.sample(frac=config.downsampling)

    del sim

    return df_sampled


def filter_dataframe(df: pd.DataFrame, config: ConfigProcessRead) -> pd.DataFrame:
    filtered_df = df.copy()

    for var_name, var_config in config.variables.items():

        if var_config.selected:
            if var_name in ["x", "y", "z"]:
                print(
                    f"Filtering {var_name} with thresholds {var_config.thr_min_sel} and {var_config.thr_max_sel}"
                )
                # Filter the DataFrame based on the specified thresholds
                filtered_df = filtered_df[
                    (filtered_df[var_name] >= var_config.thr_min_sel)
                    & (filtered_df[var_name] <= var_config.thr_max_sel)
                ]
            else:
                print(
                    f"Setting {var_name} values to 0 if outside thresholds {var_config.thr_min_sel} and {var_config.thr_max_sel}"
                )
                filtered_df.loc[
                    (filtered_df[var_name] < var_config.thr_min_sel)
                    | (filtered_df[var_name] > var_config.thr_max_sel),
                    var_name,
                ] = 0

    return filtered_df


def convertToDataframe(
    path, config: ConfigProcessRead, family=None
) -> pd.DataFrame:  # Maybe needs a better name

    if getFileType(path) == "fits":
        df = fits_to_dataframe(
            path, config
        )  # When we load an observation since the available data will always be just "x,y,z,intensity" it's meaningless to drop unused axes, we always need all 4

    else:
        df = pynbody_to_dataframe(path, config, family)

    return filter_dataframe(df, config)
