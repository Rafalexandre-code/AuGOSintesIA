#%% [markdown]
# # Formulation Selection
# This script holds the code to select the formulation from the original shampoo database reported by Chitre et al. 
# that were used to validate the Qubot. To use this script the JSON file containing the formulation database needs to 
# be downloaded an saved in the same location as this script.  

#%% [markdown]
# ## Imports
# Import packages and stablish paths for subsequent file loading.
#%% IMPORTS
import pandas as pd
import numpy as np
import json
import os

# Obtain directory containing all formulations
FOLDER = 'scripts'
PATH2ROOT = os.getcwd().split(FOLDER)[0]


# Obtain data directory for all the experiments
# (portable across Windows/Linux/macOS; override with QUBOT_DATA_DIR if data/ lives elsewhere)
main_dir = os.path.join(os.environ.get('QUBOT_DATA_DIR', os.path.join(PATH2ROOT, 'data')), 'shampoo')



#%% [markdown]
# ## Selection function definition
# Selection is based in a scoring each of the reported formulations based on the following criteria:
# 1. Maximal Coverage: Subset of  formulations with larger variety of reagents are preferred.
# 3. Redundancy: Subset of formulations that at least use each reagent at least twice are preferred.
# 4. Balance: Penalize subset of formulations that do not attempt to cover a balanced presence for each reagent
# 5. Reagent absence count: Penalize subset of formulations that are missing one or more reagents. 
#%%

def greedy_selection_custom_score(
    df, 
    category_label, 
    category_column='Category', 
    n_select=4,
    weight_coverage=0.5,
    weight_redundancy=1,
    weight_balance=2,
    weight_absence=1
):
    # Filter and drop category column
    subset = df[df[category_column] == category_label].copy()
    subset = subset.drop(columns=[category_column])
    
    selected_idx = []
    
    for _ in range(n_select):
        best_score = -np.inf
        best_idx = None

        for idx, row in subset.iterrows():
            if idx in selected_idx:
                continue

            # Check if volumes are divisible by 1000
            if row[row>0].apply(lambda x: x%1000>100).sum() != len(row[row>0].apply(lambda x: x%1000>100)):
                continue 
            # Build candidate selection
            combo_indices = selected_idx + [idx]
            combo_data = subset.loc[combo_indices]

            # 1. Reagent presence count
            presence = (combo_data > 0).sum(axis=0)

            # 2. Coverage: reagents used at least once
            coverage = (presence >= 1).sum()

            # 3. Redundancy: reagents used at least twice
            redundancy = (presence >= 2).sum()

            # 4. Balance: average std dev across reagents
            imbalance = (combo_data>0).std(axis=0).mean()

            #  5. Reagent absence count
            absence = (combo_data.sum(axis=0)==0).sum()

            # Final score 
            if len(selected_idx)==0:
                # If no previous selections, set score to 0
                score = coverage
            else:
                score = (
                    weight_coverage * coverage +
                    weight_redundancy * redundancy -
                    weight_balance * imbalance - 
                    weight_absence * absence
                )
            if score > best_score:
                best_score = score
                best_idx = idx

        selected_idx.append(best_idx)
    return df.loc[selected_idx]

#%% [markdown]
# ## Formulation Selection

# This section outlines the data preprocessing and  steps used to select tested formulations
# 1. Load Formulation Dataset
# Import the primary dataset containing all formulation compositions.

# 2. Load Reagent Dictionary
# Load the reference dictionary that defines all reagents used in this study.

# 3. Filter Relevant Formulations
#       - Select only formulations that include reagents used in this study.

# 4. Handle Diluted Reagents
#       - Rename reagents to indicate when they are in a diluted form.
#       - Add a corresponding water column that accounts for dilution contributions.

# 5. Volume Calculations
# Compute the required volume (in µL) of each component needed to prepare 10 g of each formulation,
# based on composition and density.

# 6. Final Selection
#       - Select the subset of formulations to be experimentally tested.
#       - Save the processed dataset.

#%% LOAD FORMULATION DATASET 

dataset_path = os.path.join(main_dir, 'LiquidFormulationsDataset_2023.json')
if not os.path.exists(dataset_path):
    raise FileNotFoundError(
        f"{dataset_path} not found. Download the Liquid Formulations Dataset (Chitre et al., Sci Data 11, 728, 2024; "
        "https://doi.org/10.6084/m9.figshare.c.7132624) and save it with this name.")
with open(dataset_path) as f:
    data = json.load(f)
df_all = pd.DataFrame(data)
             
df_all.set_index('ID', inplace=True,drop=True)

#%% LOAD DICTIONARY CONTAINING THE REAGENTS USED FOR THIS STUDY
with open(os.path.join(main_dir, 'viscous_liquids_parameters.json')) as f:
    solvents_dict = json.load(f) 

solvents = [solvent.split('Diluted')[-1].strip() for solvent in solvents_dict.keys()]
solvents = list(set(solvents))
solvents.remove('Water')
solvents.remove('default')

#%% FILTER FROM THE ORIGINAL FORMULATIONS ONLY ENTRIES THAT CONTAIN THE REAGENTS DEFINED IN THE REAGENT DICTIONARY
dataset_solvents = list(df_all.columns[:-6])
remove_solvents = [sol for sol in dataset_solvents if sol not in solvents]
df_selected = df_all[df_all.loc[:, remove_solvents].sum(axis=1)==0].copy()
df_selected = df_selected.drop(columns=remove_solvents)
df_selected = df_selected.reset_index()
df_selected.rename(columns={"ID":"Original ID"},inplace=True)
df_selected.index.name = 'New ID'
#%% CHANGE NAME TO DILUTED IF THE REAGENT WAS DILUTED AND ADD WATER COLUMN

df_selected_diluted = df_selected.copy()
for solvent in solvents:
    if f'Diluted {solvent}' in solvents_dict.keys():
        solvent_in_dict = f'Diluted {solvent}'
        df_selected_diluted.rename(columns={solvent: solvent_in_dict}, inplace=True)
        df_selected_diluted[solvent_in_dict] = df_selected_diluted[solvent_in_dict]*2
        solvent = solvent_in_dict

df_selected_diluted.insert(loc=12, column='Water', value=100-df_selected_diluted.iloc[:, 1:12].sum(axis=1))
#%% CALCULATE MICROLITERS REQUIRED TO PREPARE 10G OF FORMULATION
df_selected_ul = df_selected_diluted.copy()
df_selected_ul.iloc[:, 1:13] = df_selected_ul.iloc[:, 1:13]/10

for column in df_selected_ul.iloc[:, 1:13].columns:
    df_selected_ul[column] = df_selected_ul[column]/solvents_dict[column]['density']*1000
#%% SELECT AND SAVE FORMULATIONS TO BE TESTED 
df_selected_ul_for_sampling = df_selected_ul.copy()
df_selected_ul_for_sampling.drop(columns=['Original ID', 'Turbidity_NTU', 'Turbidity_Error', 'Viscosity', 'Rheology_Type','Rheology_Data'],inplace=True)

selected_df_true = greedy_selection_custom_score(df_selected_ul_for_sampling, category_label=True, category_column='Stability_Test', n_select=6)
selected_df_false = greedy_selection_custom_score(df_selected_ul_for_sampling, category_label=False, category_column='Stability_Test', n_select=6)
target_formulations = pd.concat([df_selected_ul.loc[selected_df_true.index], df_selected_ul.loc[selected_df_false.index]])
target_formulations.to_csv('Formulations.csv')
