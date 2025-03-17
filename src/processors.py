import pandas as pd
from spectral_cube import SpectralCube
from api.models import ConfigProcessRead
from src.utils import getFileType
from src.loaders import loadObservation, loadSimulation
import pynbody


def fits_to_dataframe(path):
    # Load the spectral cube
    cube = loadObservation(path)

    # Get the world coordinates for each pixel
    world_coords = cube.world[:, :, :]

    # Extract velocity, RA, and Dec from the world coordinates
    velo = world_coords[0].value
    dec = world_coords[1].value
    ra = world_coords[2].value

    # Flatten the data and coordinates
    data_flat = cube.filled_data[:].value.flatten()
    velo_flat = velo.flatten()
    ra_flat = ra.flatten()
    dec_flat = dec.flatten()

    df = pd.DataFrame(
        {"velocity": velo_flat, "ra": ra_flat, "dec": dec_flat, "intensity": data_flat}
    )

    df.dropna(inplace=True)

    del cube

    return df


def pynbody_to_dataframe(path, config: ConfigProcessRead, family=None):

    sim = loadSimulation(path, family)

    sim.physical_units()

    keys = ["x", "y", "z"]

    for key, value in config.variables.items():
        if value.selected:
            keys = keys + [key]

    data = {}

    for key in keys:
        data[key] = sim[key].astype(float)

    df = pd.DataFrame(data)

    del sim

    return df


def filter_dataframe(df: pd.DataFrame, config: ConfigProcessRead) -> pd.DataFrame:
    filtered_df = df.copy()

    for var_name, var_config in config.variables.items():

        if var_config.selected:
            # Filter the DataFrame based on the specified thresholds
            filtered_df = filtered_df[
                (filtered_df[var_name] >= var_config.thr_min)
                & (filtered_df[var_name] <= var_config.thr_max)
            ]

    return filtered_df


def convertToDataframe(
    path, config: ConfigProcessRead, family=None
) -> pd.DataFrame:  # Maybe needs a better name

    if getFileType(path) == "fits":
        df = fits_to_dataframe(
            path
        )  # When we load an observation since the available data will always be just "x,y,z,intensity" it's meaningless to drop unused axes, we always need all 4

    else:
        df = pynbody_to_dataframe(path, config, family)

    return filter_dataframe(df, config)
