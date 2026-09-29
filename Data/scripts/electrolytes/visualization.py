#%%[markdown]
#%%[markdown]
# # Visualization of polymer workflow experiments
# This notebook is used to visualize the results of the polymer workflow experiments and to generate plots included in the publication.
# To load the data, make sure the data folder included in the repository is saved in the same directory as the scripts folder. 

# The visualization includes:
# - Transfer error for reagent plot: Figure 6A
# - Mass transfer measurements of formulations: Figure 6B
# - Digestion analysis of formulations: Figure 6C
# - Thickness measurements of formulations: Figure S18 and Figure 6D
# - Conductivity measurements of formulations: Figure 6E-F and Figure S19
#%%[markdown]
# # Import libraries and load data
# In this section, we import the necessary libraries and load the data from the summary.csv file, which contains the data obtained from the polymer workflow experiments. 

#%% 
#Import libraries and load data
import os
import math
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.ticker as ticker
plt.style.use("seaborn-v0_8-colorblind")

FOLDER = 'scripts'
PATH2REPO = os.getcwd().split(FOLDER)[0]

DATA_DIR = os.environ.get('QUBOT_DATA_DIR', os.path.join(PATH2REPO, 'data'))
df_summary = pd.read_csv(os.path.join(DATA_DIR, 'electrolytes', 'summary.csv'))
#%% [markdown]
# # Plot transfer data for liquid mass transfers
# In this section, we plot the transfer data obtained from the liquid mass transfers of the polymer workflow experiments.
#%% Figure 6A: Histogram of transfer errors for liquid mass transfers by reagent.

# Extract transfer error data for each experiment
df_reagent_by_log = df_summary[~df_summary.duplicated(['Name','Log'])]
data = [df_reagent_by_log[column].dropna() for column in df_reagent_by_log.columns if 'transfer error' in column]
n_bins =np.arange(-12,2)  

fig, ax = plt.subplots(figsize=(2.6,2), dpi=300)  
ax.hist(
    data,
    bins=n_bins, 
    # density=True,
    stacked= True,  
    edgecolor="black", 
    linewidth=0.6, 
    alpha=0.8,
)


# Format plot 
# Labels
ax.set_xlabel("Percentage Error (%)", fontsize=9)
ax.set_ylabel("Count", fontsize=9)
# Bounds
y_bound = round(np.histogram(data,n_bins)[0].max()*1.125)
ax.set_ybound(0,y_bound)
# Ticks
ax.set_yticks(range(0,y_bound,2))
ax.tick_params('both', labelsize=7)
ax.minorticks_on()
ax.xaxis.set_minor_locator(ticker.AutoMinorLocator(2))
ax.yaxis.set_minor_locator(ticker.AutoMinorLocator(2))
ax.grid(True, which="major", axis="y", linestyle="--", linewidth=0.5, alpha=0.7, color='black')

fig.show()



#%% [markdown]
# # Mass transfer measurements of formulations
# In this section, we plot the mass transfer measurements obtained from the distribution of formulations to coincells during the polymer workflow experiments.
#%% Figure 6B: Histogram of mass transfer measurements for formulations distributed to coincells.
# Extract reagent mass transfer data measured during distribution of formulations to coincells
data_range = df_summary['Mass'].dropna().max()-df_summary['Mass'].dropna().min()
n_bins = data_range // 5
bins = np.arange(df_summary['Mass'].dropna().min()-df_summary['Mass'].dropna().min()%5, 
                 df_summary['Mass'].dropna().max()+5-df_summary['Mass'].dropna().max()%5, 
                 5)
# Plot histogram for all recipes
fig, ax = plt.subplots(figsize=(2.6,2), dpi=300)  
ax.hist(
    df_summary['Mass'].dropna(),
    bins=bins, 
    # density=True, 
    color="steelblue", 
    edgecolor="black", 
    linewidth=0.6, 
    alpha=0.8,
)


# Calculate key metrics and add lines in plot
mean_mass = df_summary['Mass'].dropna().mean()
median_mass =df_summary['Mass'].dropna().median()
std_dev = df_summary['Mass'].dropna().std()
ax.axvline(x=mean_mass, linewidth=1.5, linestyle=":", color="red",label='mean')
ax.axvline(x=median_mass, linewidth=1.5, linestyle=":", color="orange",)
ax.axvspan(mean_mass+std_dev, mean_mass-std_dev,alpha=0.3, color='green')

# Format plot 
# Bounds
y_bound = round(np.histogram(df_summary['Mass'],bins)[0].max()*1.125)
ax.set_ybound(0,y_bound)
# Labels
ax.set_xlabel("Mass (mg)", fontsize=9)
ax.set_ylabel("Count", fontsize=9)
# Ticks
ax.set_yticks(range(0,y_bound,5))
ax.tick_params('both', labelsize=7)
ax.grid(True, which="major", axis="y", linestyle="--", linewidth=0.5, alpha=0.7, color='black')
ax.minorticks_on()



fig.show()
#%% [markdown]
# # Digestion analysis of cured polymer electrolyte samples
# In this section, we plot the digestion analysis of cured polymer electrolyte 
# samples obtained from the polymer workflow experiments. 
# We calculate the expected mass loss for each formulation based on the initial and final 
# recorded masses of the electrolytes before and after digestion analysis. 
# We then compare the expected mass loss with the measured mass loss to calculate 
# the polymer conversion for each formulation. The expected mass loss is corrected for the transfer 
# errors of the reagents during the formulation of the electrolytes.
# Finally, we plot the distribution of polymer conversion for all formulations.
#%% Figure 6C: Histogram of polymer conversion for cured polymer electrolyte samples obtained from digestion analysis.

metric = 'Polymer Conversion Corrected %' # select y-axis
# Define expected mass loss depending on formulation composition
expected_mass_loss = {0:20,1:55.6,2:63.6,3:42.9,4:50,5:66.7,6:60,7:33.3}
df_summary['Expected Mass Loss'] = df_summary['Name'].apply(lambda x: expected_mass_loss[x])
# Corect for the mass differences caused by the liquid transfer errors of each reagent 
corrected_electrolyte_mass = df_summary['Expected Mass Loss']+df_summary['PC-LiBOB transfer error']
corrected_monomer_mass = 100- df_summary['Expected Mass Loss']+df_summary['BPAEDMA_540 transfer error']
df_summary['Expected Mass Loss Corrected'] = corrected_electrolyte_mass/(corrected_electrolyte_mass+corrected_monomer_mass)*100

#Calculate Polymer conversion 
df_summary['Mass Loss %'] = df_summary['Mass Loss']/df_summary['Electrolyte initial']*100
df_summary['Mass Loss Error %'] = df_summary['Expected Mass Loss'] - df_summary['Mass Loss %']
df_summary['Mass Loss Error Corrected %'] = df_summary['Expected Mass Loss Corrected']-df_summary['Mass Loss %'] 
df_summary['Polymer Conversion %'] = 100+df_summary['Mass Loss Error %'] 
df_summary['Polymer Conversion Corrected %'] = 100+df_summary['Mass Loss Error Corrected %'] 


#Plot histogram
recipes = df_summary.Name.unique()
recipes.sort()
# define colors for each recipe
colors = [
    "#0072B2", "#009E73", "#D55E00", "#CC79A7",
    "#F0E442", "#56B4E9", "#FF3300", "#000000"
]

colors = [
    "#0072B2", "#009E73", "#D55E00", "#CC79A7",
    "#F0E442", "#56B4E9", "#FF3300", "#000000"
]


number_bins = 18 
digestion_data = [df_summary.where(df_summary.Name==recipe)[metric].dropna() for recipe in recipes] 
x_min = np.array(digestion_data).flatten().min()
x_max = np.array(digestion_data).flatten().max()
bins = np.linspace(x_min-x_min%10,x_max+10-x_max%10,number_bins)
y_max = np.histogram(np.array(digestion_data).flatten(),bins)[0].max()

fig, ax = plt.subplots(figsize=(2.6,2), dpi=300)  
bins = np.linspace(df_summary[metric].min(),df_summary[metric].max(),number_bins)
ax.hist(
    digestion_data,
    bins=bins, 
    stacked = True,
    color=colors,
    edgecolor='black', 
    linewidth=0.6, 
    alpha=0.75,
)
# Format plot 
# Bounds
y_bound = y_max*1.125
ax.set_ybound(0,y_bound)
x_min = np.array(digestion_data).flatten().min()
x_max = np.array(digestion_data).flatten().max()
x_bounds = (x_min-x_min%10,x_max+x_max%10)
ax.set_xbound(x_bounds[0],x_bounds[1])


# Labels
ax.set_xlabel(metric, fontsize=9)
ax.set_ylabel("Count", fontsize=9)
# Ticks
ax.set_yticks(np.arange(0,y_bound+1,10))
ax.set_xticks(np.arange(int(x_bounds[0]),int(x_bounds[1]+1),10))
ax.tick_params('both', labelsize=6)
ax.grid(True, which="major", axis="y", linestyle="--", linewidth=0.5, alpha=0.7, color='black')
ax.minorticks_on()

fig.show()
#%% [markdown]
# # Thickness measurements of electrolyte layers
# In this section, we plot the thickness measurements of electrolyte layers obtained from 
# automated and manual measurements during the polymer workflow experiments. 
# We compare the distribution of thickness measurements obtained from automated and manual measurements 
# to evaluate the performance of the automated measurement method. 
# We also plot the distribution of differences between automated and manual thickness measurements 
# to evaluate the accuracy of the automated measurement method.
#%% Figure S18: Histogram of thickness measurements for electrolyte layers obtained from automated and manual measurements.

# Spcify number of bins and bin size for histograms 
number_bins = 24
# Obtain data for all measurements to obtain max and min thickness to calculate bins
df_thickness = pd.DataFrame([df_summary[x].dropna() for x in df_summary.columns if 'Thickness' in x]).transpose()
all_thickness = np.array([df_thickness.dropna()[x] for x in df_thickness.columns if 'Thickness' in x]).flatten()
# Calculate bins 
bins = np.linspace(all_thickness.min(),all_thickness.max(),number_bins)

fig, ax = plt.subplots(1,1,figsize=(2.6,2), dpi=300)  
ax.hist(
    df_summary['Electrolyte Thickness Automated'].dropna(),
    bins=bins, 
    # density=True, 
    color="green", 
    edgecolor="black", 
    linewidth=0.6, 
    alpha=0.5,
    label= 'Automated Low Boundary'
)

ax.hist(
    df_summary['Electrolyte Thickness Manual'].dropna(),
    bins=bins, 
    # density=True, 
    color="blue", 
    edgecolor="black", 
    linewidth=0.6, 
    alpha=0.5,
    label= 'Manual'
)


# Format plot 
#Bounds
y_bound = round(np.histogram( df_summary['Electrolyte Thickness Manual'].dropna(),bins)[0].max()*1.25)
ax.set_ybound(0,y_bound)
# Labels
ax.set_xlabel("Thickness [mm]", fontsize=9)
ax.set_ylabel("Count", fontsize=9)
# Ticks
ax.set_yticks(np.arange(0,y_bound,5))
ax.tick_params('both', labelsize=7)
ax.minorticks_on()
#Grid
ax.grid(True, which="major", axis="y", linestyle="--", linewidth=0.5, alpha=0.7, color='black')

fig.show()


#%% Figure 6D: Histogram of differences between automated and manual thickness measurements for electrolyte layers.

# Spcify number of bins and bin size for histograms 
number_bins = 24
# Obtain data for all measurements to obtain max and min thickness to calculate bins
df_thickness = pd.DataFrame([df_summary[x].dropna() for x in df_summary.columns if 'Thickness' in x]).transpose()
all_differences = np.array([df_thickness.dropna()['Electrolyte Thickness Manual']-df_thickness.dropna()[x]  for x in df_thickness.columns if 'Thickness' in x]).flatten()
# Calculate bins 
bins = np.linspace(all_differences.min(),all_differences.max(),number_bins)

fig, ax = plt.subplots(1,1,figsize=(2.6,2), dpi=300)  
ax.hist(
    df_summary['Electrolyte Thickness Manual'].dropna()- df_summary['Electrolyte Thickness Automated'].dropna(),
    bins=bins, 
    # density=True, 
    color="yellow", 
    edgecolor="black", 
    linewidth=0.6, 
    alpha=0.5,
    label= 'Automated Low Boundary'
)


# Format plot 
#Bounds
y_bound = max(
    round(np.histogram(df_summary['Electrolyte Thickness Automated'].dropna()-df_summary.dropna()['Electrolyte Thickness Manual'],bins)[0].max()),
    np.histogram(df_summary['Electrolyte Thickness Automated'].dropna()-df_summary.dropna()['Electrolyte Thickness Manual'],bins)[0].max())
y_bound = y_bound*1.125
ax.set_ybound(0,y_bound)
# Labels
ax.set_xlabel("Thickness [mm]", fontsize=9)
ax.set_ylabel("Count", fontsize=9)
# Ticks
ax.set_yticks(np.arange(0,y_bound,5))
ax.tick_params('both', labelsize=7)
ax.minorticks_on()
#Grid
ax.grid(True, which="major", axis="y", linestyle="--", linewidth=0.5, alpha=0.7, color='black')

fig.show()


#%% [markdown]
# # Conductivity measurements of cured polymer electrolyte samples
# In this section, we plot the conductivity measurements of cured polymer electrolyte samples obtained 
# from the polymer workflow experiments.
#
# We calculate the conductivity of the electrolyte samples based on the thickness measurements and 
# the EIS parameters obtained from the EIS analysis of the samples.
#
# We then plot the conductivity measurements across their liquid electrolyte composition 
# to evaluate the effect of the electrolyte composition on the conductivity of the samples.
#%% # Figure 6E-F: Conductivity measurements of cured polymer electrolyte samples across their liquid electrolyte composition at zero strain

strains = [0]
fig_0, ax_0 = plt.subplots(len(strains),figsize=(2.6, 2*len(strains)), dpi=300)  
fig_1, ax_1 = plt.subplots(len(strains),figsize=(2.6, 2*len(strains)), dpi=300)  

if len(strains)==1:
    ax_0 = [ax_0]
    ax_1 = [ax_1]

# define colors for each recipe
colors = [
    "#0072B2", "#009E73", "#D55E00", "#CC79A7",
    "#F0E442", "#56B4E9", "#FF3300", "#000000"
]

# Calculate conductivity and plot for each strain
for i,strain in enumerate(strains):
    df_conductivity = df_summary.loc[:,['Name','Log','Electrolyte Thickness Automated',f'EIS parameters strain {strain}','Expected Mass Loss']].copy()
    df_conductivity.rename(columns={'Electrolyte Thickness Automated':'Thickness'}, inplace=True)
    df_conductivity[f'EIS parameters strain {strain}']= df_conductivity[f'EIS parameters strain {strain}'].apply(lambda x: x.replace(' ',','))
    df_conductivity[f'EIS parameters strain {strain}']= df_conductivity[f'EIS parameters strain {strain}'].apply(lambda x: np.nan if x == '[nan]' else x)
    df_conductivity['R0'] = df_conductivity[f'EIS parameters strain {strain}'].apply(lambda x: eval(x)[0] if isinstance(x, str) and len(eval(x))>=1 else np.nan)
    df_conductivity['R1'] = df_conductivity[f'EIS parameters strain {strain}'].apply(lambda x: eval(x)[1] if isinstance(x, str) and len(eval(x))>=2 else np.nan)    
    df_conductivity['sigma0'] = df_conductivity['Thickness']*0.1/(df_conductivity['R0']*(math.pi*0.5**2))  # S/cm
    df_conductivity['sigma1'] = df_conductivity['Thickness']*0.1/( (df_conductivity['R1'])*(math.pi*0.5**2))  # S/cm    


    recipes = df_conductivity.Name.unique()
    recipes.sort()
    color_dict = dict(zip(recipes, colors))

# Plot sigma_0 conductivity for each recipe and electrolyte composition   
    for label, group in df_conductivity.groupby("Name"):
        # calculate mean, median and std for sigma_0, ignoring NaN values and replacing them with 0 for the calculation of the metrics
        mean =  (group.dropna()['sigma0']*1000).describe().apply(lambda x: 0 if np.isnan(x) else x)['mean']
        median=(group.dropna()['sigma0']*1000).describe().apply(lambda x: 0 if np.isnan(x) else x)['50%']
        std=(group.dropna()['sigma0']*1000).describe().apply(lambda x: 0 if np.isnan(x) else x)['std']
        
        ax_0[i].errorbar(y= mean,
            x= group['Expected Mass Loss'].iloc[0],
            yerr= std,
            fmt='o',
            c='black',
            markerfacecolor = color_dict[label],
            markeredgecolor = color_dict[label],
            )

        

    # Labels
    ax_0[i].set_ylabel("Conductivity (mS/cm)", fontsize=9)
    # Ticks
    ax_0[i].tick_params('both',labelsize=7)
    ax_0[i].minorticks_on()
    ax_0[i].grid(True, which="major", axis="y", linestyle="--", linewidth=0.5, alpha=0.7, color='black')
    

# Plot sigma_1 conductivity for each recipe and electrolyte composition   
    for label, group in df_conductivity.groupby("Name"):
        # calculate mean, median and std for sigma_1, ignoring NaN values and replacing them with 0 for the calculation of the metrics
        mean =  (group.dropna()['sigma1']*1000).describe().apply(lambda x: 0 if np.isnan(x) else x)['mean']
        median=(group.dropna()['sigma1']*1000).describe().apply(lambda x: 0 if np.isnan(x) else x)['50%']
        std=(group.dropna()['sigma1']*1000).describe().apply(lambda x: 0 if np.isnan(x) else x)['std']
        
        ax_1[i].errorbar(y= mean,
            x= group['Expected Mass Loss'].iloc[0],
            yerr= std,
            fmt='o',
            c='black',
            markerfacecolor = color_dict[label],
            markeredgecolor = color_dict[label],
            )

    # Format plot 
    # Labels
    ax_1[i].set_ylabel("Conductivity (mS/cm)", fontsize=9)
    # Ticks
    ax_1[i].minorticks_on()
    ax_1[i].tick_params('both', labelsize=7)
    ax_1[i].grid(True, which="major", axis="y", linestyle="--", linewidth=0.5, alpha=0.7, color='black')


ax_0[-1].set_xlabel("Electrloyte Composition [%]", fontsize=9)
ax_1[-1].set_xlabel("Electrloyte Composition [%]", fontsize=9)

fig_0.show()
fig_1.show()
#%% Figure S19: Conductivity measurements of cured polymer electrolyte samples across their liquid electrolyte composition for different strains.



strains = [0, 1, 2.5, 5, 10]
fig_0, ax_0 = plt.subplots(1,len(strains),figsize=(8,2.6), sharex=True, sharey=True, dpi=300)  
fig_1, ax_1 = plt.subplots(1, len(strains),figsize=(8,2.6), dpi=300, sharex=True, sharey=True)  

# define colors for each recipe
colors = [
    "#0072B2", "#009E73", "#D55E00", "#CC79A7",
    "#F0E442", "#56B4E9", "#FF3300", "#000000"
]

# Calculate conductivity and plot for each strain
for i,strain in enumerate(strains):
    df_conductivity = df_summary.loc[:,['Name','Log','Electrolyte Thickness Automated',f'EIS parameters strain {strain}','Expected Mass Loss']].copy()
    df_conductivity.rename(columns={'Electrolyte Thickness Automated':'Thickness'}, inplace=True)
    df_conductivity[f'EIS parameters strain {strain}']= df_conductivity[f'EIS parameters strain {strain}'].apply(lambda x: x.replace(' ',','))
    df_conductivity[f'EIS parameters strain {strain}']= df_conductivity[f'EIS parameters strain {strain}'].apply(lambda x: np.nan if x == '[nan]' else x)
    df_conductivity['R0'] = df_conductivity[f'EIS parameters strain {strain}'].apply(lambda x: eval(x)[0] if isinstance(x, str) and len(eval(x))>=1 else np.nan)
    df_conductivity['R1'] = df_conductivity[f'EIS parameters strain {strain}'].apply(lambda x: eval(x)[1] if isinstance(x, str) and len(eval(x))>=2 else np.nan)    
    df_conductivity['sigma0'] = df_conductivity['Thickness']*0.1/(df_conductivity['R0']*(math.pi*0.5**2))  # S/cm
    df_conductivity['sigma1'] = df_conductivity['Thickness']*0.1/( (df_conductivity['R1'])*(math.pi*0.5**2))  # S/cm    


    recipes = df_conductivity.Name.unique()
    recipes.sort()
    colors = [
        "#0072B2", "#009E73", "#D55E00", "#CC79A7",
        "#F0E442", "#56B4E9", "#FF3300", "#000000"
    ]

    color_dict = dict(zip(recipes, colors))
    
# Plot sigma_0 conductivity for each recipe and electrolyte composition   
    for label, group in df_conductivity.groupby("Name"):
        mean =  (group.dropna()['sigma0']*1000).describe().apply(lambda x: 0 if np.isnan(x) else x)['mean']
        median=(group.dropna()['sigma0']*1000).describe().apply(lambda x: 0 if np.isnan(x) else x)['50%']
        std=(group.dropna()['sigma0']*1000).describe().apply(lambda x: 0 if np.isnan(x) else x)['std']
        
        ax_0[i].errorbar(y= mean,
            x= group['Expected Mass Loss'].iloc[0],
            yerr= std,
            fmt='o',
            c='black',
            markerfacecolor = color_dict[label],
            markeredgecolor = color_dict[label],
            )
        
        ax_0[i].scatter(
            y= group['sigma0'].apply(lambda x: 0 if np.isnan(x) else x) * 1000,
            x= group['Expected Mass Loss'],
            color = color_dict[label],
            alpha=0.4,
            edgecolor='none'
        )

    # Ticks
    ax_0[i].tick_params('both',labelsize=7)
    ax_0[i].minorticks_on()
    ax_0[i].grid(True, which="major", axis="y", linestyle="--", linewidth=0.5, alpha=0.7, color='black')

# Plot sigma_1 conductivity for each recipe and electrolyte composition   
    for label, group in df_conductivity.groupby("Name"):
        mean =  (group.dropna()['sigma1']*1000).describe().apply(lambda x: 0 if np.isnan(x) else x)['mean']
        median=(group.dropna()['sigma1']*1000).describe().apply(lambda x: 0 if np.isnan(x) else x)['50%']
        std=(group.dropna()['sigma1']*1000).describe().apply(lambda x: 0 if np.isnan(x) else x)['std']
        
        ax_1[i].errorbar(y= mean,
            x= group['Expected Mass Loss'].iloc[0],
            yerr= std,
            fmt='o',
            c='black',
            markerfacecolor = color_dict[label],
            markeredgecolor = color_dict[label],
            )
        
        ax_1[i].scatter(
            y= group['sigma1'].apply(lambda x: 0 if np.isnan(x) else x) * 1000,
            x= group['Expected Mass Loss'],
            color = color_dict[label],
            alpha=0.4,
            edgecolor='none'
        )

    # Format plot 
    # Ticks
    ax_1[i].minorticks_on()
    ax_1[i].tick_params('both', labelsize=7)
    ax_1[i].grid(True, which="major", axis="y", linestyle="--", linewidth=0.5, alpha=0.7, color='black')

# Labels
for fig in [fig_0, fig_1]:
    fig.supxlabel('Electrloyte Composition [%]',y=0.05,fontsize=9)
    fig.supylabel('Conductivity [mS/cm]',fontsize=9,y=0.6)
    fig.tight_layout(pad=1.0, w_pad=0.25) 
    fig.show()


# %%
