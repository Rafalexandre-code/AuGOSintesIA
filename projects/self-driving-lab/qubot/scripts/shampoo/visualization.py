#%%[markdown]
# # Formulation Workflow Visualization
# This notebook creates publication-quality figures to visualize key performance metrics from formulation experiments.
# It generates histograms for mass transfer accuracy and pH adjustment results.
#
#  To load the data, make sure the data folder included in the repository is saved in the same directory as the scripts folder. 

#%% [markdown]
# ## Imports and data path loading
# This section imports the necessary libraries and loads the data paths for all the formulation experiments.

#%%
#Import libraries
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
plt.style.use("seaborn-v0_8-colorblind")
import os
import glob
from pathlib import Path
import re

# Obtain data directory for all the experiments

FOLDER = 'scripts'
PATH2ROOT = os.getcwd().split(FOLDER)[0]


# Obtain data directory for all the experiments
# (portable across Windows/Linux/macOS; override with QUBOT_DATA_DIR if data/ lives elsewhere)
main_dir = os.path.join(os.environ.get('QUBOT_DATA_DIR', os.path.join(PATH2ROOT, 'data')), 'shampoo')
experiment_paths = sorted(p for p in Path(main_dir).glob("*") if p.is_dir())

df_summary = pd.read_csv(os.path.join(main_dir, 'summary.csv'))
#%%[markdown]
# ## Mass transfer accuracy histogram
# This section visualizes the distribution of mass transfer errors across all reagent dispensing operations.
# The histogram shows the percentage error for all transfer events.

#%% # Figure S15: Mass transfer error histogram

# Extract transfer error data for each experiment
data = [df_summary[column] for column in df_summary.columns if 'transfer error' in column]
data = np.array(data).flatten()
data = data[~np.isnan(data)]
n_bins = 24 


fig, ax = plt.subplots(figsize=(2.6,2), dpi=300)  
ax.hist(
    data,
    bins=n_bins, 
    color="steelblue", 
    edgecolor="black", 
    linewidth=0.6, 
    alpha=0.8,
)


# Format plot 
# Bounds
y_bound = round(np.histogram(data,n_bins)[0].max()*1.25)
ax.set_ybound(0,y_bound)
x_bounds = (round(data.min()), round(data.max()))
# Labels
ax.set_xlabel("Percentage Error [%]", fontsize=9)
ax.set_ylabel("Count", fontsize=9)
# Ticks
ax.tick_params('both', labelsize=7)
ax.grid(True, which="major", axis="y", linestyle="--", linewidth=0.5, alpha=0.7, color='black')
fig.show()

# Visualization of data with errors below 20% 
# Extract transfer error data for each experiment
data = [df_summary[column] for column in df_summary.columns if 'transfer error' in column]
data = np.array(data).flatten()
data = data[~np.isnan(data)]
n_bins = 24 
data = data[np.abs(data) < 20]

fig, ax = plt.subplots(figsize=(2.6,2), dpi=300)  
ax.hist(
    data,
    bins=n_bins, 
    color="steelblue", 
    edgecolor="black", 
    linewidth=0.6, 
    alpha=0.8,
)


# Format plot 
# Bounds
y_bound = round(np.histogram(data,n_bins)[0].max()*1.25)
ax.set_ybound(0,y_bound)
x_bounds = (round(data.min()), round(data.max()))
# Labels
ax.set_xlabel("Percentage Error [%]", fontsize=9)
ax.set_ylabel("Count", fontsize=9)
# Ticks
ax.tick_params('both', labelsize=7)
ax.grid(True, which="major", axis="y", linestyle="--", linewidth=0.5, alpha=0.7, color='black')
fig.show()


#%% [markdown]
# ## pH adjustment histogram    
# This section visualizes the final pH values achieved across all formulation experiments.

# %% Figure S17: Final pH histogram with tolerance range highlighted

n_bins = 12 


fig, ax = plt.subplots(figsize=(3, 2), dpi=300)  # Adjust for journal column width
ax.hist(
    df_summary['Final pH'],
    bins=n_bins, 
    color="steelblue", 
    edgecolor="black", 
    linewidth=0.6, 
    alpha=0.8,
)

# Add green box for tolerance area
ax.axvspan(5.6, 6, color='green', alpha=0.3)

# Format plot 
# Labels
ax.set_xlabel("pH", fontsize=9)
ax.set_ylabel("Count", fontsize=9)
# Ticks
ax.tick_params('both', labelsize=8)
ax.grid(True, which="major", axis="y", linestyle="--", linewidth=0.5, alpha=0.7, color='black')
ax.minorticks_on()

fig.show()

# %%
