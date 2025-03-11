import pandas as pd
from spectral_cube import SpectralCube
from api.models import ConfigProcessRead
from src.utils import getFileType
import pynbody


def fits_to_dataframe(path):
    # Load the spectral cube
    cube = SpectralCube.read(path)

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

    # Create a DataFrame
    df = pd.DataFrame(
        {"velocity": velo_flat, "ra": ra_flat, "dec": dec_flat, "intensity": data_flat}
    )

    df.dropna(inplace=True)

    del cube

    return df


def pynbody_to_dataframe(file, config: ConfigProcessRead):

    # Load the simulation file
    sim = pynbody.load(file)

    # Ensure the simulation is in physical units
    sim.physical_units()

    # Default keys to always include
    keys = ["x", "y", "z"]

    # Combine default keys with requested keys
    for key, value in config.variables.items():
        if value.selected:
            keys = keys + [key]

    # Initialize dictionary to store data
    data = {}

    # Extract each key's data
    for key in keys:
        data[key] = sim[key].astype(float)  # Convert to float for DataFrame

    # Create a DataFrame
    df = pd.DataFrame(data)

    del sim

    return df


def filter_dataframe(df: pd.DataFrame, config: ConfigProcessRead) -> pd.DataFrame:
    # Start with the original DataFrame
    filtered_df = df.copy()

    # Apply the filtering for each variable in the config
    for var_name, var_config in config.variables.items():
        if var_config.selected:
            # Filter the DataFrame based on the specified thresholds
            filtered_df = filtered_df[
                (filtered_df[var_name] >= var_config.thr_min)
                & (filtered_df[var_name] <= var_config.thr_max)
            ]

    return filtered_df


def convertToDataframe(path, config=None) -> pd.DataFrame:  # Maybe needs a better name

    if getFileType(path) == "fits":
        df = fits_to_dataframe(path)

    else:
        df = pynbody_to_dataframe(path, config)

    return filter_dataframe(df, config)
