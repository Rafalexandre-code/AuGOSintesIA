#%%[markdown]
# # Analysis of shampoo formulation workflow experiments
# This notebook is used to analyze the results of the formulation workflow experiments.
# The analysis includes:
# - Mass transfer measurements
# - pH adjustment tracking
# - Stability classification from 24 h stability data
# - Aggregated recipe summary export

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
main_dir = f'{PATH2ROOT}\data\shampoo'
experiment_paths = [p for p in Path(main_dir).glob("*") if p.is_dir()]

#%% [markdown]
# ## Mass transfer measurements
# The mass transfer measurements are used to determine the accuracy of the liquid handling system.
# The measurements are done by measuring the mass of the liquid before and after the transfer.

#%% Mass transfer measurements of formulation experiments
# Extract reagent transfer data

df_summary_rt = pd.DataFrame()

for path in experiment_paths:
    try:
        df = pd.read_csv(str(path) + r'\Summary_transfers.csv')
    
    except FileNotFoundError:
        print(f"File not found: {str(path) + r'\Summary_transfers.csv'}")
        continue
        
    df['Log'] = path.name
    df['Well'] = df['destination'].apply(lambda x: x.split(' ')[0])

    if not df_summary_rt.empty:
        df_summary_rt.columns = df.columns

    df_summary_rt= pd.concat([df_summary_rt, df], ignore_index=True)   


#%% [markdown]
# ## pH adjustment tracking
# This section loads each formulation pH adjustment log, extracts the initial and final pH values,
# and counts the number of additions made during pH adjustment for each sampled well.

# %%PH analysis

# PH analysis of formulation experiments
df_ph_summary = pd.DataFrame()

for path in experiment_paths:
    ph_csvs = glob.glob(fr'{path}\*pH_adjustment.csv')
    for csv in ph_csvs:
        ph_adjustment_df = pd.read_csv(csv)
        df_ph = pd.DataFrame(columns=['Log', 'Recipe', 'Well', 'Initial_pH', 'Final_pH', 'Number of additions'])
        df_ph['Log'] = [path.name]
        df_ph['Recipe'] = [csv.split('\\')[-1].split('_')[2]]
        df_ph['Well'] = [csv.split('\\')[-1].split('_')[1]]
        df_ph['Initial_pH'] = [ph_adjustment_df['pH of Sample'].iloc[0]]
        df_ph['Final_pH'] = [ph_adjustment_df['pH of Sample'].iloc[-1]]
        df_ph['Number of additions'] = [len(ph_adjustment_df) - 1]  # Subtract 1 to exclude the initial measurement
        if not df_ph_summary.empty:
            df_ph_summary.columns = df_ph.columns
        df_ph_summary= pd.concat([df_ph_summary, df_ph], ignore_index=True)
    



    
#%% [markdown]
# ## Stability analysis
# This section reads the stability results log, filters the 24-hour stability entries, and assigns a stability label for each recipe.
# It also extracts the associated log and well identifiers from the input file names.

# %% Stability analysis of formulation experiments
df_analysis = pd.read_csv(main_dir+r'\stability.csv')
df_analysis_24h = df_analysis.where(df_analysis['description'].str.contains('24h')).dropna().copy()
df_analysis_24h.reset_index(inplace=True,drop=True)
df_analysis_24h['Log']= df_analysis_24h['input'].apply(lambda x: re.findall(r'\d{8}_\d{4}',x)[0])
df_analysis_24h['Well']= df_analysis_24h['input'].apply(lambda x: re.findall(r'[AB]\d',x)[0])

df_analysis_24h['Stability'] = df_analysis_24h['output'].apply(lambda x: 'Unstable' if 'Unstable' in x else 'Stable')
df_analysis_24h['Recipe'] = df_analysis_24h['description'].apply(lambda x: x.split('-')[-1].split(' ')[0])      
df_analysis_24h['Sample_id'] = df_analysis_24h['input'].apply(lambda x: x.split('_')[-1].split('.')[0])  
df_analysis_24h_grouped = df_analysis_24h.groupby(['Recipe', 'Stability']).size().reset_index(name='Counts').set_index('Recipe')

for recipe in df_analysis_24h_grouped.index.unique():
    df_recipe = df_analysis_24h_grouped.loc[[recipe]]
    if len(df_recipe) == 1:
        stability = df_recipe['Stability'].values[0]
    else:
        stable_count = df_recipe[df_recipe['Stability'] == 'Stable']['Counts'].values[0]
        unstable_count = df_recipe[df_recipe['Stability'] == 'Unstable']['Counts'].values[0]
        stability = 'Stable' if stable_count >= unstable_count else 'Unstable'
        print(df_recipe)
    print(f"Recipe: {recipe}, Stability: {stability}")

    
    
#%% [markdown]
# ## Summary aggregation
# This final section merges mass transfer errors, pH adjustment results, and stability labels into a single summary table.
# The consolidated output is exported to `summary.csv` for downstream reporting.

#%%
df_summary = df_analysis_24h.loc[:,['Log','Well','Stability','Recipe']].copy()
for log in df_summary.Log.unique():
    df_log_recipe_rt = df_summary_rt.where(df_summary_rt.Log==log).dropna(how='all').copy()
    for well in df_log_recipe_rt.Well.unique():
        idx = df_log_recipe_rt['Well'].str.contains(well,na=False)
        df_recipe_rt = df_log_recipe_rt[idx].copy().set_index('reagent')    
        recipes_idx = df_summary.where((df_summary.Log == log) & (df_summary.Well.str.contains(well))).dropna(how='all').index  
        for i in range(df_recipe_rt.shape[0]):
            df_summary.loc[recipes_idx, f'{df_recipe_rt.index[i]} transfer error'] = df_recipe_rt.loc[df_recipe_rt.index[i],'%error']
    
    df_log_recipe_ph = df_ph_summary.where(df_ph_summary.Log==log).dropna(how='all').copy()
    for well in df_log_recipe_ph.Well.unique():
        idx = df_log_recipe_ph['Well'].str.contains(well,na=False)
        recipes_idx = df_summary.where((df_summary.Log == log) & (df_summary.Well.str.contains(well))).dropna(how='all').index  
        df_summary.loc[recipes_idx, 'Initial pH'] = df_log_recipe_ph[idx]['Initial_pH'].values[0]
        df_summary.loc[recipes_idx, 'Final pH'] = df_log_recipe_ph[idx]['Final_pH'].values[0]

df_summary.to_csv(f'{main_dir}/summary.csv', index=False)

