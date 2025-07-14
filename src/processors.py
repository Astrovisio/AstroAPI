import numpy as np
import polars as pl
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
        df = pl.from_pandas(Table(table[col]).to_pandas())
        df.columns = [str(i) for i in range(len(df.columns))]
        df = df.with_row_index("y").with_columns(pl.col("y").cast(pl.UInt16))
        df = df.unpivot(index="y", variable_name="x").with_columns(pl.col("x").cast(pl.UInt16))
        df = df.with_columns(pl.lit(col.split("col")[1], pl.UInt16).alias("z"))
        df = df.remove(pl.col("value") == 0).drop_nulls(subset=["value"])
        df = df["x", "y", "z", "value"]
        output.append(df)

    df = pl.concat(output)[["x", "y", "z", "value"]]

    del cube, table
    if not config:
        return df
    df_sampled = df.sample(fraction=config.downsampling)

    return df_sampled


def pynbody_to_dataframe(path, config: ConfigProcessRead, family=None):
    sim = loadSimulation(path, family)

    sim.physical_units()

    data = {}

    for key, value in config.variables.items():
        if value.selected:
            if "-" in key:
                key, i = key.split("-")
                data[f"{key}-{i}"] = pl.Series(sim[key][:, int(i)], dtype=pl.Float32)

            else:
                data[key] = sim[key].astype(float)

    df = pl.DataFrame(data)

    df_sampled = df.sample(fraction=config.downsampling)

    del sim

    return df_sampled


def filter_dataframe(df: pl.DataFrame, config: ConfigProcessRead) -> pl.DataFrame:
    filtered_df: pl.DataFrame = df.clone()

    for var_name, var_config in config.variables.items():
        if var_config.selected and var_config.thr_min_sel and var_config.thr_max_sel:
            filtered_df = filtered_df.filter(pl.col(var_name).is_between(var_config.thr_min_sel, var_config.thr_max_sel))

    return filtered_df


def convertToDataframe(path, config: ConfigProcessRead, family=None) -> pl.DataFrame:  # Maybe needs a better name
    if getFileType(path) == "fits":
        df = fits_to_dataframe(path, config)  # When we load an observation since the available data will always be just "x,y,z,value" it's meaningless to drop unused axes, we always need all 4

    else:
        df = pynbody_to_dataframe(path, config, family)

    return filter_dataframe(df, config)
