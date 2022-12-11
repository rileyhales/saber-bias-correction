import glob
import os
from collections.abc import Iterable
from typing import List
import yaml
import logging

import pandas as pd
from natsort import natsorted

logger = logging.getLogger(__name__)

# file paths used in this project which should come from the config file
workdir = ''
x_fdc_train = ''
x_fdc_all = ''
drain_gis = ''
gauge_gis = ''
gauge_data = ''
hindcast_zarr = ''

# processing options
n_processes = 1

# assign table and gis_input file required column names
mid_col = 'model_id'  # model id column name: in drain_table, gauge_table, regulate_table, cluster_table
gid_col = 'gauge_id'  # gauge id column name: in gauge_table
rid_col = 'reg_id'  # regulate id column name: in regulate_table
cid_col = 'clstr_id'  # cluster column name: in cluster_table

order_col = 'strahler_order'  # strahler order column name: in drain_table
x_col = 'x_mod'  # x coordinate column name: in drain_table
y_col = 'y_mod'  # y coordinate column name: in drain_table
down_mid_col = 'downstream_model_id'  # downstream model id column name: in drain_table

rprop_col = 'rprop'  # regulated stream propagation: created by assign_table
gprop_col = 'gprop'  # gauged stream propagation: created by assign_table
asn_mid_col = 'asgn_mid'  # assigned model id column name: in assign_table
asn_gid_col = 'asgn_gid'  # assigned gauge id column name: in assign_table
reason_col = 'reason'  # reason column name: in assign_table

all_cols = [mid_col,
            gid_col,
            rid_col,
            order_col,
            x_col,
            y_col,
            rprop_col,
            gprop_col,
            cid_col,
            down_mid_col,
            asn_mid_col,
            asn_gid_col,
            reason_col, ]

atable_cols = [asn_mid_col, asn_gid_col, reason_col, rprop_col, gprop_col]
atable_cols_defaults = ['unassigned', 'unassigned', 'unassigned', '', '']

# discharge dataframe columns names
DF_QOBS = 'Qobs'
DF_QMOD = 'Qmod'
DF_QSIM = 'Qsim'

# required workdir folders
DIR_TABLES = 'tables'
DIR_GIS = 'gis'
DIR_CLUSTERS = 'clusters'
DIR_VALID = 'validation'

# name of the required input tables and the outputs
TABLE_ASSIGN = 'assign_table.parquet'
TABLE_DRAIN = 'drain_table.parquet'
TABLE_GAUGE = 'gauge_table.parquet'
TABLE_REGULATE = 'regulate_table.csv'
TABLE_MIDS = 'mid_table.parquet'
TABLE_GIDS = 'gid_table.parquet'
# todo make this MID GID RID and only use this table
table_mid_gid_map = 'mid_gid_map_table.parquet'

# tables produced to cache results during propagation
TABLE_PROP_RESOLVED = 'prop_table_resolved.parquet'
TABLE_PROP_DOWN = 'prop_table_downstream.parquet'
TABLE_PROP_UP = 'prop_table_upstream.parquet'

# tables generated by the clustering functions
TABLE_CLUSTER_METRICS = 'cluster_metrics.csv'
TABLE_CLUSTER_SSCORES = 'cluster_sscores.csv'
TABLE_CLUSTER_LABELS = 'cluster_labels.parquet'
CLUSTER_COUNT_JSON = 'best-fit-cluster-count.json'

# tables produced by the bootstrap validation process
TABLE_ASSIGN_BTSTRP = 'assign_table_bootstrap.csv'
TABLE_BTSTRP_METRICS = 'bootstrap_metrics.csv'

GENERATED_TABLE_NAMES_MAP = {
    "assign_table": TABLE_ASSIGN,
    "drain_table": TABLE_DRAIN,
    "gauge_table": TABLE_GAUGE,
    "regulate_table": TABLE_REGULATE,
    "assign_table_bootstrap": TABLE_ASSIGN_BTSTRP,
    "bootstrap_metrics": TABLE_BTSTRP_METRICS,
    "cluster_metrics": TABLE_CLUSTER_METRICS,
    "cluster_sscores": TABLE_CLUSTER_SSCORES,
    "cluster_table": TABLE_CLUSTER_LABELS,
}

VALID_YAML_KEYS = {
    'workdir',
    'x_fdc_train',
    'x_fdc_all',
    'drain_gis',
    'gauge_gis',
    'gauge_data',
    'hindcast_zarr',
    'n_processes',

    'mid_col',
    'gid_col',
    'rid_col',
    'cid_col',
}


def read_config(config: str) -> None:
    """
    Read the config file to set paths and values

    Args:
        config: path to the config file

    Returns:
        None
    """
    # open a yml and read to dictionary
    with open(config, 'r') as f:
        config_dict = yaml.safe_load(f)

    if config_dict is None:
        raise ValueError('Config file is empty')

    # set global variables
    for key, value in config_dict.items():
        if key not in VALID_YAML_KEYS:
            logger.error(f'Ignored invalid key in config file: "{key}". Consult docs for valid keys.')
            continue
        logger.info(f'Config: {key} = {value}')
        globals()[key] = value

    # validate inputs
    if not os.path.isdir(workdir):
        logger.warning(f'Workspace directory does not exist: {workdir}')
    if not os.path.exists(drain_gis):
        logger.warning(f'Drainage network GIS file does not exist: {drain_gis}')
    if not os.path.exists(gauge_gis):
        logger.warning(f'Gauge network GIS file does not exist: {gauge_gis}')
    if not os.path.isdir(gauge_data):
        logger.warning(f'Gauge data directory does not exist: {gauge_data}')
    if not os.path.exists(hindcast_zarr):
        logger.warning(f'Hindcast zarr directory does not exist: {hindcast_zarr}')

    return


def scaffold_workdir(path: str, include_validation: bool = True) -> None:
    """
    Creates the correct directories for a Saber project within the specified directory

    Args:
        path: the path to a directory where you want to create workdir subdirectories
        include_validation: boolean, indicates whether to create the validation folder

    Returns:
        None
    """
    dir_list = [DIR_TABLES, DIR_GIS, DIR_CLUSTERS]
    if not os.path.exists(path):
        os.mkdir(path)
    if include_validation:
        dir_list.append(DIR_VALID)
    for d in dir_list:
        p = os.path.join(path, d)
        if not os.path.exists(p):
            os.mkdir(p)
    return


def get_state(prop) -> int or str:
    """
    Get a state variable provided by the config or a controlled global variable

    Args:
        prop: name of the global variable

    Returns:
        value of the global variable
    """
    assert prop in globals(), ValueError(f'"{prop}" is not a recognized project state key')
    return globals()[prop]


def get_dir(dir_name: str) -> str:
    """
    Get the path to a directory within the workspace

    Args:
        dir_name: name of the directory

    Returns:
        path to the directory
    """
    assert dir_name in [DIR_TABLES, DIR_GIS, DIR_CLUSTERS, DIR_VALID], f'"{dir_name}" is not a valid directory name'
    table_path = os.path.join(workdir, dir_name)
    if not os.path.exists(table_path):
        logger.warning(f'"{dir_name}" directory does not exist. Error imminent: {table_path}')
    return table_path


def read_table(table_name: str) -> pd.DataFrame:
    """
    Read a table from the project directory by name.

    Args:
        table_name: name of the table to read

    Returns:
        pd.DataFrame

    Raises:
        FileNotFoundError: if the table does not exist in the correct directory with the correct name
        ValueError: if the table format is not recognized
    """
    table_path = _get_table_path(table_name)
    if not os.path.exists(table_path):
        raise FileNotFoundError(f'Table does not exist: {table_path}')

    table_format = os.path.splitext(table_path)[-1]
    if table_format == '.parquet':
        return pd.read_parquet(table_path, engine='fastparquet')
    elif table_format == '.feather':
        return pd.read_feather(table_path)
    elif table_format == '.csv':
        return pd.read_csv(table_path, dtype=str)
    else:
        raise ValueError(f'Unknown table format: {table_format}')


def write_table(table: pd.DataFrame, name: str) -> None:
    """
    Write a table to the correct location in the project directory

    Args:
        table: the pandas DataFrame to write
        name: the name of the table to write

    Returns:
        None

    Raises:
        ValueError: if the table format is not recognized
    """
    table_path = _get_table_path(name)
    table_format = os.path.splitext(table_path)[-1]
    if table_format == '.parquet':
        return table.to_parquet(table_path)
    elif table_format == '.feather':
        return table.to_feather(table_path)
    elif table_format == '.csv':
        return table.to_csv(table_path, index=False)
    else:
        raise ValueError(f'Unknown table format: {table_format}')


def _get_table_path(table_name: str) -> str:
    """
    Get the path to a table in the project directory by name

    Args:
        table_name: name of the table to find a path for

    Returns:
        Path (str) to the table

    Raises:
        ValueError: if the table name is not recognized
    """
    # todo organize the table names better
    if table_name in VALID_YAML_KEYS:
        return os.path.join(workdir, globals()[table_name])
    elif table_name in GENERATED_TABLE_NAMES_MAP:
        return os.path.join(workdir, DIR_TABLES, GENERATED_TABLE_NAMES_MAP[table_name])
    elif table_name.startswith('cluster_'):
        # cluster_centers_{n_clusters}.parquet - 1 per cluster
        # cluster_sscores_{n_clusters}.parquet - 1 per cluster
        return os.path.join(workdir, DIR_CLUSTERS, f'{table_name}.parquet')
    else:
        raise ValueError(f'Unknown table name: {table_name}')


def _find_model_files(n_clusters: int or Iterable = 'all') -> List[str]:
    """
    Find all the kmeans model files in the project directory.

    Args:
        n_clusters: the number of clusters to find models for. If 'all', all models will be returned

    Returns:
        List of paths to the kmeans model files

    Raises:
        TypeError: if n_clusters is not an int, iterable of int, or 'all'
    """
    kmeans_dir = os.path.join(workdir, DIR_CLUSTERS)
    if n_clusters == 'all':
        return natsorted(glob.glob(os.path.join(kmeans_dir, 'kmeans-*.pickle')))
    elif isinstance(n_clusters, int):
        return glob.glob(os.path.join(kmeans_dir, f'kmeans-{n_clusters}.pickle'))
    elif isinstance(n_clusters, Iterable):
        return natsorted([os.path.join(kmeans_dir, f'kmeans-{i}.pickle') for i in n_clusters])
    else:
        raise TypeError('n_clusters should be of type int or an iterable')
