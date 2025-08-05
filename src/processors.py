import gc

import polars as pl
from astropy.table import Table

from api.models import ConfigProcessRead
from src.loaders import load_data
from src.utils import getFileType


def fits_to_dataframe(path, config: ConfigProcessRead = None, progress_callback=None):

    # Load the spectral cube
    with load_data(path) as obs:
        table = Table(obs[0].data)

        def expand_table(table, progress_callback=None):
            total = len(table.columns)
            for idx, col in enumerate(table.columns):
                df = pl.from_pandas(Table(table[col]).to_pandas())
                df.columns = [str(i) for i in range(len(df.columns))]
                df = df.with_row_index("y").with_columns(pl.col("y").cast(pl.UInt16))
                df = df.unpivot(index="y", variable_name="x").with_columns(
                    pl.col("x").cast(pl.UInt16)
                )
                df = df.with_columns(pl.lit(col.split("col")[1], pl.UInt16).alias("z"))
                df = df.remove(pl.col("value") == 0).drop_nulls(subset=["value"])
                df = df["x", "y", "z", "value"]
                if progress_callback:
                    progress_callback((idx + 1) / total)
                yield (df)

        df = pl.concat(expand_table(table, progress_callback))[["x", "y", "z", "value"]]

        del table

    del obs
    gc.collect()

    if config and hasattr(config, "downsampling"):
        df = df.sample(fraction=config.downsampling)

    return df


def pynbody_to_dataframe(
    path, config: ConfigProcessRead, family=None, progress_callback=None
):
    with load_data(path) as sim:

        sim.physical_units()

        def variable_series(sim, config, progress_callback=None):
            dtype = pl.Float32
            total = len(config.variables)
            for idx, (key, value) in enumerate(config.variables.items()):
                if value.selected:
                    if "-" in key:
                        base_key, i = key.split("-")
                        name = f"{base_key}-{i}"
                        arr = sim[base_key][:, int(i)]
                    else:
                        name = key
                        arr = sim[key]
                    if progress_callback:
                        progress_callback((idx + 1) / total)
                    yield pl.Series(name=name, values=arr, dtype=dtype)

        df = pl.DataFrame(variable_series(sim, config, progress_callback))

    del sim
    gc.collect()

    if config and hasattr(config, "downsampling"):
        df = df.sample(fraction=config.downsampling)

    return df


def filter_dataframe(df: pl.DataFrame, config: ConfigProcessRead) -> pl.DataFrame:
    filtered_df: pl.DataFrame = df.clone()

    for var_name, var_config in config.variables.items():
        if var_config.selected and var_config.thr_min_sel and var_config.thr_max_sel:
            filtered_df = filtered_df.filter(
                pl.col(var_name).is_between(
                    var_config.thr_min_sel, var_config.thr_max_sel
                )
            )

    return filtered_df


def convertToDataframe(
    path, config: ConfigProcessRead, family=None, progress_callback=None
) -> pl.DataFrame:
    if getFileType(path) == "fits":
        df = fits_to_dataframe(path, config, progress_callback)

    else:
        df = pynbody_to_dataframe(path, config, family, progress_callback)

    return filter_dataframe(df, config)
