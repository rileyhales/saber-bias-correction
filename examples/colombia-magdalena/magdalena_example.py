import os

import numpy as np

import hbc


np.seterr(all="ignore")

workdir = '/Users/rchales/data/regional-bias-correction/colombia-magdalena'
drain_shape = os.path.join(workdir, 'gis_inputs', 'magdalena_dl_attrname_xy.json')
gauge_shape = os.path.join(workdir, 'gis_inputs', 'ideam_stations.json')
obs_data_dir = os.path.join(workdir, 'data_inputs', 'obs_csvs')

# Only need to do this step 1x ever
# hbc.prep.scaffold_working_directory(workdir)

# Create the gauge_table and drain_table.csv
# Scripts not provided, check readme for instructions

# Generate the assignments table
# assign_table = hbc.table.gen(workdir)
# hbc.table.cache(workdir, assign_table)
# Or read the existing table
# assign_table = hbc.table.read(workdir)

# Prepare the observation and simulation data
# Only need to do this step 1x ever
# hbc.prep.historical_simulation(os.path.join(workdir, 'data_simulated', 'south_america_era5_qout.nc'), workdir)
# hbc.prep.observation_data(workdir)

# Generate the clusters using the historical simulation data
# hbc.cluster.generate(workdir)
# assign_table = hbc.cluster.summarize(workdir, assign_table)
# hbc.table.cache(workdir, assign_table)

# Assign basins which are gauged and propagate those gauges
# assign_table = hbc.assign.gauged(assign_table)
# assign_table = hbc.assign.propagation(assign_table)
# assign_table = hbc.assign.clusters_by_dist(assign_table)
# todo assign_table = hbc.assign.clusters_by_monavg(assign_table)

# Cache the assignments table with the updates
# hbc.table.cache(workdir, assign_table)

# Generate GIS files so you can go explore your progress graphically
# hbc.gis.clip_by_assignment(workdir, assign_table, drain_shape)
# hbc.gis.clip_by_cluster(workdir, assign_table, drain_shape)
# hbc.gis.clip_by_unassigned(workdir, assign_table, drain_shape)

# Compute the corrected simulation data
# assign_table = hbc.table.read(workdir)
# hbc.calibrate_region(workdir, assign_table)
# vtab = hbc.validate.gen_val_table(workdir)
hbc.gis.validation_maps(workdir, gauge_shape)
hbc.analysis.plot(workdir, obs_data_dir, 9007721)


# import pandas as pd
# path_to_your_pickle_file = '/Users/rchales/data/regional-bias-correction/colombia-magdalena/validation_runs/90/data_processed/subset_time_series.pickle'
# a = pd.read_pickle(path_to_your_pickle_file)
# a.index = a.index.tz_localize('UTC')
# a.to_pickle(path_to_your_pickle_file)


# import netCDF4 as nc
# import numpy as np
# path = '/Users/rchales/data/regional-bias-correction/colombia-magdalena/validation_runs/90/calibrated_simulated_flow.nc'
# a = nc.Dataset(path, 'r+')
# a.createVariable('corrected', 'i4', ('corrected',), zlib=True, shuffle=True, fill_value=-1)
# a['corrected'][:] = np.array((0, 1))
# a.sync()
# a.close()