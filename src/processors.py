import numpy as np
import pandas as pd
from astropy.table import Table

from api.models import ConfigProcessRead
from src.loaders import loadObservation, loadSimulation
from src.utils import getFileType


def fits_to_dataframe(path, config: ConfigProcessRead = None):

    # Load the spectral cube
    cube = loadObservation(path)
    table = Table(cube[0].data)

    output = []

    for col in table.columns:
        df = Table(table[col]).to_pandas()
        df.columns = range(len(df.columns))
        df_stacked = df.stack().reset_index()
        df_stacked.columns = ['y', 'x', 'value']
        df_stacked['z'] = int(col.split('col')[1])
        output.append(df_stacked)
        
    df = pd.concat(output)[['x', 'y', 'z', 'value']].reset_index(drop=True)
        
    del cube, table
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
