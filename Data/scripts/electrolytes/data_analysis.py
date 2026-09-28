#%%[markdown]
# # Analysis of polymer workflow experiments
# This notebook is used to analyze the results of the polymer workflow experiments.
# To use this notebook make sure the data folder included in the repository is saved in the same directory as the scripts folder.

# The analysis includes:
# - Mass transfer measurements
# - Coincell thickness measurements
# - Coincell digestion experiments
# - Coincell electrochemical experiments

#%%[markdown]
# # Import libraries and load data paths
# In this section, we import the libraries used for data cleaning, numerical analysis, plotting and circuit fitting.
#
#  We also build the root data path and enumerate the experiment folders that are analyzed throughout this notebook.
#%% IMPORTS AND LOAD DATA PATHS
import math
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
plt.style.use("seaborn-v0_8-colorblind")
import plotly.express as px
import os
import glob
from datetime import datetime
from plotly.subplots import make_subplots
import plotly.graph_objects as go
from pathlib import Path


FOLDER = 'scripts'
PATH2ROOT = os.getcwd().split(FOLDER)[0]


# Obtain data directory for all the experiments
main_dir = f'{PATH2ROOT}\Data\electrolytes'
experiment_paths = [p for p in Path(main_dir).glob("*") if p.is_dir()]

#%% [markdown]
# # Mass transfer measurements
# The mass transfer measurements are used to determine the accuracy of the liquid handling system.
#
#  This section reads reagent transfer summary files, aggregates per-experiment results, and computes transfer error percentages.

#%%
df_summary_rt = pd.DataFrame() # Create dataframe to aggregate results from each experiment
# Iterate through experiment files
for path in experiment_paths:
    
    try:
        df = pd.read_csv(str(path) + r'\Summary_transfers.csv') # Read summary of transfer for each experiment
    
    except FileNotFoundError:
        print(f"File not found: {str(path) + r'\Summary_transfers.csv'}")
        continue
    
    # Clean data   
    df['Log'] = path.name
    df['Well'] = ['A1', 'B1']*2

    # Add columns to summary dataframe
    if not df_summary_rt.empty:
        df_summary_rt.columns = df.columns

    # Add data to summary dataframe
    df_summary_rt= pd.concat([df_summary_rt, df], ignore_index=True)   

# Calculate percentage error
df_summary_rt['%error'] = df_summary_rt['error']/df_summary_rt['expected mass']*100


#%% [markdown]
# # Mass transfer measurements of formulations
# This section extracts and aggregates formulation to coincells mass transfer data.
# 
# The results are used to assess how consistently each formulation was dispensed across wells.

#%%
df_summary_ft = pd.DataFrame() # Create dataframe to aggregate results from each experiment
# Iterate through experiment files
for path in experiment_paths:
    try:
        df = pd.read_csv(str(path) + r'\Distributed_coincell.csv') # Read summary of transfer for each experiment
    
    except FileNotFoundError:
        print(f"File not found: {str(path) + r'\Distributed_coincell.csv'}")
        continue
    
    # Clean data   
    df['Log'] = path.name
    df['Well'] = ['A1', 'A2', 'A3', 'A4', 'B1', 'B2', 'B3', 'B4']

    # Add columns to summary dataframe
    if not df_summary_ft.empty:
        df_summary_ft.columns = df.columns

    # Add data to summary dataframe
    df_summary_ft= pd.concat([df_summary_ft, df], ignore_index=True)   


#%% [markdown]
# ## Analysis thickness measurements 
# This section combines manual thickness measurements with automated analysis of displacement traces.
#
# Manual thickness values are read from summary files, while displacement data is used to estimate electrolyte height automatically.
#%%
# Create a DataFrame to store the thickness data
df_summary_t = pd.DataFrame()
# Loop through each experiment path
for path in experiment_paths:
    try:
        df = pd.read_excel(str(path) + r'\Coincell_thickness.xlsx', sheet_name='Sheet1') # Read summary of thickness for each experiment

    except FileNotFoundError:
        print(f"File not found: {str(path) + r'\Coincell_thickness.csv'}")
        continue
    # Clean data
    df.dropna(how='all', inplace=True)
    df['Log'] = path.name

    # Add columns to summary dataframe
    if df_summary_t.empty:
        df_summary_t = pd.DataFrame(columns=df.columns)

    # Add data to summary dataframe
    df_summary_t = pd.concat([df_summary_t, df], ignore_index=True)

# Clean data
df_summary_t.insert(loc=1,column='Date',value = df_summary_t.Log.apply(lambda x:datetime.strptime(x, '%d%m%Y_%H%M')))
df_summary_t['Electrolyte Thickness Manual']= df_summary_t['Electrolyte and Coincell thickness']-df_summary_t['Coincell Thickness']
df_summary_t.sort_values(['Date','Well'],ascending=True, inplace=True)
df_summary_t.reset_index(inplace=True, drop=True)


#

#%%
# The function below processes force-displacement traces to find the electrode/electrolyte boundary.
# It uses a baseline second-derivative threshold to detect the final displacement and compute automated thickness.

def measure_displacement(df:pd.DataFrame, n_baseline:int=100, tolerance:int=5):
    """
    Measure displacement from force-displacement data by finding the point where the second derivative exceeds 
    a threshold based on the baseline noise.
    Args:
    df (pd.DataFrame): DataFrame containing 'Displacement' and 'Force' columns.
    n_baseline (int): Number of initial points to use for baseline noise estimation.
    tolerance (int): Multiplier for the standard deviation of the baseline to set the threshold.
    Returns:
    displacement (float): Estimated displacement at the electrode/electrolyte boundary.
    """
    first_index = df.where(df.Displacement==df.Displacement.max()).dropna(how='all').index[-1]
    final_index = df.where(df.Displacement==df.Displacement.min()).dropna(how='all').index[0]
    df = df.loc[first_index:final_index].copy()
    deriv_2nd = df['Force'].diff().diff()
    deriv_2nd = deriv_2nd.dropna()
    std_baseline = deriv_2nd.iloc[:n_baseline].std()
    # Find the first index where the second derivative is within the tolerance of the standard deviation
    # of the baseline   
    points_above_t = deriv_2nd[~deriv_2nd.between(-tolerance*std_baseline, tolerance*std_baseline)]
    if points_above_t.size==0:
        print("No points found above the tolerance threshold.")
        return 'nan'
    displacement = df['Displacement'].loc[points_above_t.index[0]]
   
    return displacement

#%% Calculate automated thickness values and compare with manual measurements

# iterate through experiment paths to read coincell and electrolyte displacement data
for path in experiment_paths:
    coincell_paths = glob.glob(str(path) + r'\displacement\*coincell*.csv') # empty coincell
    electrolyte_paths = glob.glob(str(path) + r'\displacement\*electrolyte*.csv') # coincell + electrolyte
    
    for coincell_path, electrolyte_path in zip(coincell_paths, electrolyte_paths):
        try:
            df_coincell = pd.read_csv(coincell_path)
            df_electrolyte = pd.read_csv(electrolyte_path)
        except FileNotFoundError:
            print(f"File not found: {coincell_path} or {electrolyte_path}")
            continue
        
        log = coincell_path.split('\\')[-3]
        well = coincell_path.split('_')[-4]+ coincell_path.split('_')[-3]

        df_subset = df_summary_t.where(df_summary_t['Log'] == log).dropna(how='all')
        df_subset = df_subset.where(df_subset['Well'] == well).dropna(how='all')
        thickness_high = -measure_displacement(df_coincell) + measure_displacement(df_electrolyte) # calculate thickness from displacements
        df_summary_t.loc[df_subset.index, 'Electrolyte Thickness Automated'] = thickness_high 

df_summary_t['Difference'] = df_summary_t['Electrolyte Thickness Manual'] - df_summary_t['Electrolyte Thickness Automated']

#%% [markdown]
# # Digestion analysis
# This section reads coin cell digestion summary files and aggregates initial/final mass values.
# The computed mass loss quantifies electrolyte and cell material changes during digestion experiments.

#%% Digestion analysis
df_summary_d = pd.DataFrame()
for path in experiment_paths: 
    try:
        df = pd.read_excel(str(path) + r'\Coincell_digestion.xlsx',sheet_name='Sheet1')
    
    except FileNotFoundError:
        print(f"File not found: {str(path) + r'\Coincell_digestion.xlsx'}")
        continue
        
    df['Log'] = path.name

    if df_summary_d.empty:
        df_summary_d = pd.DataFrame(columns=df.columns)

    df_summary_d= pd.concat([df_summary_d, df], ignore_index=True)
    df_summary_d.reset_index(inplace=True, drop=True)
#%% [markdown]
# # EIS analysis
# This section processes electrochemical impedance spectroscopy (EIS) data.
# It cleans raw impedance spectra, validates them with Kramers-Kronig checks, segments the Nyquist plot,
# fits equivalent circuit elements, and computes chi-squared goodness-of-fit metrics.

#%% Impedance analysis 

# Imports
from scipy.signal import argrelextrema, savgol_filter
from impedance.validation import linKK
from impedance.models import circuits
from impedance.models.circuits.fitting import rmse
from sklearn.linear_model import LinearRegression
from scipy.signal import find_peaks


def load_df(df):
        """
        Extract the relevant columns from data and transform to relevant analysis values 

        Args:
            df (pd.DataFrame): raw data
            instrument (Optional[str], optional): name of instrument to match column names. Defaults to None.

        Returns:
            pd.DataFrame: dataframe of relevant data columns
        """
        # Calculate Impedance magnitude 
        df['Impedance magnitude [ohm]'] = df['abs( Voltage ) [V]'] / df['abs( Current ) [A]']
        
        # Calculate real and imaginary components 
        polar = list(zip(df['Impedance magnitude [ohm]'].to_list(), df['Impedance phase [rad]'].to_list()))
        df['Real'] = [p[0]*math.cos(p[1]) for p in polar]
        df['Imaginary'] = [p[0]*math.sin(p[1]) for p in polar]
        
        df = df[['Frequency [Hz]', 'Real', 'Imaginary']].copy()
        df.columns = ['Frequency', 'Real', 'Imaginary']
        df.dropna(inplace=True)
        df['Frequency_log10'] = np.log10(df['Frequency'])
        df['Impedance'] = df['Real'] + 1j*df['Imaginary']
        df['Magnitude'] = df['Impedance'].abs()
        df['Magnitude_log10'] = np.log10(df['Magnitude'])
        df['Phase'] = df['Impedance'].map(lambda z : math.phase(z)/math.pi*180)
        df['Impedance_polar'] = list(zip(df['Magnitude'], df['Phase']))
        return df
    

# Utility functions 
def nudge_points(x_values:np.ndarray, y_values:np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """
    Nudge points to avoid curve from looping on itself

    Args:
        x_values (np.ndarray): x values
        y_values (np.ndarray): y values

    Returns:
        tuple[np.ndarray, np.ndarray]: nudged x values; nudged y values
    """
    for i in range(0, len(x_values)-2):
        if x_values[i] > x_values[i+1]:
            x_diff = x_values[i] - x_values[i+1]
            x_values[i+1:] += x_diff
        if i== 0:
            continue
    return x_values, y_values

def find_segments(x,y):
    """
    Find segments in EIS data based on second derivative analysis.
    The analysis works best when only the positive imaginary data is used 
    and the data has been smoothened by a convolution or Savitzky-Golay filter.
    Parameters:
    x (np.array): Real part of impedance data.
    y (np.array): Imaginary part of impedance data.

    Returns:
    dict: Dictionary with segment start and end indices.
    """
    #Calculate first and second derivatives
    dxdy = np.gradient(y, x)
    d2xdy2 =np.gradient(dxdy,x)
    #Create dictionary to hold segment indices
    idxs = {}
    count=0 # Segment counter
    #Find peaks in second derivative that indicate potential segment boundaries
    maximums = list(find_peaks(d2xdy2)[0])
    idxs[count] = {'start':0}   

    #loop through identified peaks to determine valid segment boundaries
    for i,idx in enumerate(maximums):
        #Determine window size used to analyse trends 
        if i == len(maximums)-1:
            window = (idx,len(y)-1)
        else:
            window = (idx,maximums[i+1])
        # Check if first derivative is constant in the window
        # If constant segment has been found
        # If all following points have a higher value for 
        # first derivative we reached the end of all segments
        if sum(dxdy[idx:-2]>=dxdy[idx]) == len(dxdy[idx:-2]):                      
            idxs[count]['end'] = idx+1
            count += 1
            idxs[count]= {}
            idxs[count]['start'] = idx+2
            print(f'{idx} ending because increasing derivative')
            break

        if dxdy[window[0]:window[1]].std()<dxdy[np.quantile(dxdy,0.75)>dxdy].std()/10:
            idxs[count]['end'] = idx
            count += 1
            idxs[count]= {}
            idxs[count]['start'] = idx+1
            continue

        # Check if first derivative is decreasing in the window
        # If decreasing derivative in segment boundary found
        # we have reached the end of a segment
        if dxdy[window[0]] - dxdy[window[1]-1]<0:                        
            idxs[count]['end'] = idx+1
            count += 1
            idxs[count]= {}
            idxs[count]['start'] = idx+2
            print('stopping because decreasing derivative')
            continue 

        elif d2xdy2[window[0]]-np.mean(d2xdy2[window[0]:window[1]-1])<0:
            maximums.remove(idx)
            continue
    idxs[count]['end'] = len(y)-1
    
    #Check if there are linear adjacent segments and merge them
    last_linear = False
    list_of_pop_counts = []
    for i_count,count in enumerate(list(idxs.keys())):
        if dxdy[idxs[count]['start']:idxs[count]['end']].std()<dxdy[np.quantile(dxdy,0.75)>dxdy].std()/10:
            if last_linear==False:
                last_linear = count
            else:
                print(f'Merging linear segments at index {count} with index {last_linear}')
                idxs[last_linear]['end'] = idxs[count]['end']
                list_of_pop_counts.append(count)
                continue
        else:
            last_linear = False 
             
    for key in list_of_pop_counts:
        idxs.pop(key)
        
    for key in list(idxs.keys()):
        if idxs[key]['end'] - idxs[key]['start'] <5:
            del idxs[key]
        

    return idxs


def calculate_parameters(x,y,segments,df):
    """
    Calculate parameters of linear and semicircle fits of each parsed segment.
    Parameters:
    x (np.array): Real part of impedance data used for segmentation.
    y (np.array): Imaginary part of impedance data used for segmentation.
    segments (dict): Dictionary with segment start and end indices.
    df (pd.DataFrame): Original EIS data containing frequency and impedance values.
    """
    #iterate through segments and categorize as linear or semicircle
    for segment in segments.values():
        #Select segment data
        x_segment = x[segment['start']:segment['end']]
        y_segment = y[segment['start']:segment['end']]
        #Estimate initial parameters for semicircle fitting
        if np.argmin(y_segment)==0:
            R0 = x_segment[0] 
        elif x_segment[argrelextrema(y_segment, np.less)].size>0:
            R0 = x_segment[argrelextrema(y_segment, np.less)[0][0]]
        else:
            R0 = x_segment[0]
        R1 = x_segment[np.argmax(y_segment)] + R0
        C = 1/y_segment[np.argmax(y_segment)]
        n_list = [0.85,0.9,0.95]
        frequency = df['Frequency'].iloc[segment['start']:segment['end']].to_numpy()
        impedance = df['Impedance'].iloc[segment['start']:segment['end']].to_numpy()
        n=None
        for i in n_list:
            circuit_semicircle = circuits.CustomCircuit(name='RC Circuit (CPE)', circuit='R0-p(R1,CPE1)', initial_guess=[R0,R1,C,i])
            circuit_semicircle.fit(frequency, impedance)
            fitted_semicircle = circuit_semicircle.predict(frequency)
            rmse_semicircle = rmse(impedance, fitted_semicircle)
            if n==None:
                n=i
                best_rmse = rmse_semicircle
            elif rmse_semicircle<best_rmse:
                n=i
                best_rmse = rmse_semicircle
        #Fit linear model and calculate RMSE
        circuit_linear = LinearRegression().fit(x_segment.reshape(-1, 1), y_segment.reshape(-1, 1))  
        fitted_linear = circuit_linear.predict(x_segment.reshape(-1, 1))
        rmse_linear = rmse(y_segment, fitted_linear.reshape(-1))
        print(f"Segment from {segment['start']} to {segment['end']}: RMSE Linear={rmse_linear}, RMSE Semicircle={rmse_semicircle}")
        segment['linear_parameters'] = [1/np.max(y_segment),math.atan(circuit_linear.coef_[0][0])*2/math.pi]
        segment['semicircle_parameters'] = circuit_semicircle.parameters_
    return segments


def select_parameters(circuit_diagram,segments):
    """
    Select parameters for each segment based on the expected elements from the tested equivalent circuit
    Parameters:
    circuit_diagram (str): Equivalent circuit diagram representation as a string.
    segments (dict): Dictionary with segments start and end indices and fitted parameters (i.e. linear and semicircle fits)
    """
    guess_parameters = []
    counter = 0
    number_of_segments = len(segments)
    number_of_circuit_elements = len(circuit_diagram.split('-'))
    if number_of_segments+1!=number_of_circuit_elements:
        print('Warning: Number of segments is less than number of circuit elements. Default combination of segments will be used')
        difference = number_of_segments - (number_of_circuit_elements-1)
        if difference>0:
            for i in range(difference):
                print(f'Removing segment at index {list(segments.values())[1]} to match circuit elements')
                list(segments.values())[0]['end'] = list(segments.values())[1]['end']
                segments.pop(list(segments.keys())[1])
 
        else:
            print('Cannot automatically adjust segments to match circuit elements. Please review segmentation.')    
            return None
    for i,subcircuit in enumerate(circuit_diagram.split('-') ):
        if i==0 and 'R' in subcircuit and 'p' not in subcircuit:
            guess_parameters.append(list(segments.values())[i]['semicircle_parameters'][0])

        elif 'p' in subcircuit:
            guess_parameters = guess_parameters + list(list(segments.values())[counter]['semicircle_parameters'][1:])
            counter +=1

        elif 'W' in subcircuit:
            guess_parameters = guess_parameters + list(list(segments.values())[counter]['linear_parameters'][0])
            counter +=1

        else:
            guess_parameters = guess_parameters + list(list(segments.values())[counter]['linear_parameters'])
            counter +=1

    return guess_parameters

def chi_squared_eis(
    Z_exp,
    Z_fit,
    n_params,
    alpha=None,
    frequency=None,
    reduced=True
    ):
    """
    Weighted chi-squared for EIS using modulus weighting.

    Parameters
    ----------
    Z_exp : complex ndarray
        Experimental impedance
    Z_fit : complex ndarray
        Fitted impedance
    n_params : int
        Number of fitted parameters

    alpha: float
        Weighting value 
    
    reduced : bool
        Return reduced chi-squared

    Returns
    -------
    chi2 : float
    """
    Z_exp = np.asarray(Z_exp)
    Z_fit = np.asarray(Z_fit)

    # Calculate chi2 for real and imaginary impedances
    chi2_real = ((Z_exp.real - Z_fit.real)/np.abs(Z_exp))**2 
    chi2_imag= ((Z_exp.imag - Z_fit.imag)/np.abs(Z_exp))**2
    
   # Calculate chi2    
    if alpha and  (frequency != None): # Bias chi2 to be sensitive to discrepancies at high frequency values 
        chi2 = np.sum(chi2_real*frequency**alpha)+np.sum(chi2_imag*frequency**alpha)

    else:
        chi2 = np.sum(chi2_real)+np.sum(chi2_imag)
    if reduced:
        dof = 2 * len(Z_exp) - n_params
        return chi2 / dof
    



    return chi2




#%%

# Automatically estimate the parameters of a EIS raw spectrum the code loops through each experiment file to:
# 1. Load and transform data
# 2. Assess quality of the data based on KK parameters
# 3. Segment data based on 
# 4. Estimate linear and semicircle fits for each segment
# 5. Exctract for each segment the parameters according the target circuit diiagaram 
# 6. Fit and calculate chi2 of the spectrum 
# 7. Evaluate chi2 and HFchi2 if not good manually fit parameters


eis_summary_df = pd.DataFrame(columns=['log','well', 'strain', 'parameters','chi_value','chi_value_HF','segments','outcome'])
exception=[]
circuit_diagram = 'R0-p(R1,CPE1)-CPE2'
counter = 0 
counter_good = 0
counter_bad = 0
counter_fail = 0
for i,directory in enumerate(experiment_paths[:]):
    for j,csv in enumerate(glob.glob(main_dir + rf'\{directory}\EIS\*.csv')[:]):
        df = pd.read_csv(csv, header=0)
        df=df.rename(columns={'abs_voltage':'abs( Voltage ) [V]','abs_current':'abs( Current ) [A]','impedance_phase':'Impedance phase [rad]','impedance_modulus':'Impedance magnitude [ohm]','frequency':'Frequency [Hz]'})
        eis_analysis = load_df(df, instrument='Biologic')
        test2 = eis_analysis.df.copy()        
        # 2. Filter data to positive imaginary
        test2['Imaginary'] = test2['Imaginary'] * -1
        test2.where(test2.Imaginary>0, inplace=True)
        test2.dropna(how='all', inplace=True)   
        test2 = test2.iloc[:-10,:]
        eis_analysis.df = eis_analysis.df.loc[test2.index,:]
        test2y =test2.loc[:,'Imaginary'].to_numpy()
        test2x = test2.loc[:,'Real'].to_numpy()

        # 3. Evaluate if data is suitable for analysis
        frequency = test2['Frequency'].to_numpy()
        impedance = test2['Impedance'].to_numpy() 
        

        M, mu, Z_linKK, res_real, res_imag = linKK(frequency, impedance, c=.5, max_M=100, fit_type='complex', add_cap=True)
        
        if round(np.abs(res_imag).mean()*100)>5 or round(np.abs(res_real).mean()*100)>5:
            parameters = [np.nan]
            chi_value = [np.nan]
            chi_value_HF = [np.nan]
            outcome = 'Fail'

       
        else:

            convtest2x,convtest2y =nudge_points(savgol_filter(test2x.copy(),5,1),savgol_filter(test2y.copy(),5,1))
   
            x = convtest2x.copy()
            y = convtest2y.copy()   


            # 5. Find segments based on second derivative

            segments = find_segments(x,y)
            print(segments)
            guess = calculate_parameters(x, y, segments, test2)



            intial_guess_list = select_parameters(circuit_diagram, guess)

            if intial_guess_list is None:
                first_key = list(segments.keys())[0]
                intial_guess_list = list(segments[first_key]['semicircle_parameters'])+[segments[first_key]['linear_parameters'][0]]+[0.9]
            
            circuit = circuits.CustomCircuit(name='Full Circuit', circuit=circuit_diagram, initial_guess=intial_guess_list)
            frequency = test2['Frequency']
            impedance = test2['Impedance']
            try:
                circuit.fit(frequency, impedance)
                fitted = circuit.predict(frequency) 
                parameters = circuit.parameters_
                chi_value = chi_squared_eis(impedance,fitted,len(intial_guess_list))
                chi_value_HF = chi_squared_eis(impedance,fitted,len(intial_guess_list),frequency=frequency,alpha=1)
                # chi_value_LF = chi_squared_eis(impedance,fitted,len(intial_guess_list),frequency=frequency,alpha=)
                
            except Exception as e:
                exception.append((i,j,e))
                parameters = [np.nan]
                chi_value = [np.nan]
                chi_value_HF = [np.nan]
                outcome= 'Fail'

            if  (chi_value!=[np.nan] and chi_value_HF!=[np.nan]):

                if (chi_value>0.001 and chi_value_HF>15):
                    fig = make_subplots(specs=[[{"secondary_y": True}]])
                    fig.update_layout(title=f'Real Residual: {np.abs(res_real).mean()*100:.2f} Imag Residual:{np.abs(res_imag).mean()*100:.2f}')
                    
                    fig.add_trace(
                                go.Scatter(x=test2x, 
                                y=test2y, 
                                mode='markers',
                                name=f'Data',
                                text = list(range(len(convtest2x))) ,
                                hovertemplate=(
                                "Real: %{x}<br>"
                                "Imag: %{y}<br>"
                                "Index: %{text}<br>"
                            ) 
                                ))
                                        
                    fig.add_trace(
                                go.Scatter(x=fitted.real, 
                                            y=fitted.imag*-1, 
                                mode='markers',
                                name=f'Fit 1', 
                                customdata=[chi_value]*len(fitted),
                                text=   [chi_value_HF]*len(fitted),
                                hovertemplate=(
                                    "Real: %{x}<br>"
                                    "Imag: %{y}<br>"
                                    "chi_value: %{customdata}<br>"
                                    "chi_value_HF %{text}<br>"
                                )
                                ))

                    
                    fig.update_layout(
                        width=600,
                        height=600
                    )
                    
                    fig.update_layout(
                        xaxis=dict(scaleanchor="y", scaleratio=1),
                        yaxis=dict(constrain="domain")
                    )

                    print(csv)
                    fig.show()
                    answer = input('Please input fail, good or start points for segments eg. 22')
                    if answer.isdigit()==False:
                        invalid=False
                        if answer not in ['fail','good','break']:
                            invalid = True
                        while invalid:
                            answer = input('Please input fail, good or start points for segments eg. 22')
                            if answer in ['fail','good','break']:
                                invalid = False
                            elif answer.isdigit():
                                invalid = False 
                                
                    if answer == 'fail':
                        parameters = [np.nan]
                        chi_value = [np.nan]
                        chi_value_HF = [np.nan]

                    elif answer == 'good':
                        outcome = 'Good'

                    elif answer.isdigit():
                        while answer.isdigit():
                            end = input('Please input end of las segment eg. 34 or esc for default')
                            if end == '':
                                end= len(convtest2x)-1
                            elif end.isdigit():
                                end=int(end)
                             
                            answer = int(answer)
                            segments={0:{'start':0,
                                            'end':answer},
                                        1:{'start':answer+1,
                                            'end':end}  
                                        }                         

                            guess = calculate_parameters(x, y, segments, test2)
                            intial_guess_list = select_parameters(circuit_diagram, guess)

                            circuit = circuits.CustomCircuit(name='Full Circuit', circuit=circuit_diagram, initial_guess=intial_guess_list)
                            circuit.fit(frequency, impedance)
                            fitted = circuit.predict(frequency) 
                            chi_value = chi_squared_eis(impedance,fitted,len(intial_guess_list))
                            chi_value_HF = chi_squared_eis(impedance,fitted,len(intial_guess_list),frequency=frequency,alpha=1)
                            parameters = circuit.parameters_
                            fig.add_trace(
                                    go.Scatter(x=fitted.real, 
                                        y=fitted.imag*-1, 
                                        mode='markers',
                                        name=f'Fitted 2',
                                        customdata=[chi_value]*len(fitted),
                                        text=   [chi_value_HF]*len(fitted),
                                        hovertemplate=(
                                            "Real: %{x}<br>"
                                            "Imag: %{y}<br>"
                                            "chi_value: %{customdata}<br>"
                                            "chi_value_HF %{text}<br>"
                                            )
                                        ) 
                                    )
                            fig.show()
                            answer = input('Please if good, bad fit good or start points for segments eg. 22')
                        if  answer  in ['good','bad']:
                            outcome = answer.capitalize()
                            while answer not in ['good','bad']:
                                answer = input('Please input if good or bad fit')
                                outcome = answer.capitalize() 

                    else:
                        break
                                            

                else:
                    outcome = 'Good'

        well = csv.split('_channel_')[0][-1] + str(int(csv.split('_channel_')[1][0])+1)
        log = directory
        strain = csv.split('_strain_')[-1].split('_')[0]
        
        eis_summary_df = pd.concat([eis_summary_df, pd.DataFrame({'log':[log],'well':[well],'strain':[strain],'parameters':[parameters],'chi_value':[chi_value],'chi_value_HF':[chi_value_HF], 'segments':str(segments), 'outcome':outcome})], ignore_index=True)
        counter+=1 
        if outcome== 'Fail':
             counter_fail += 1
        elif outcome == 'Bad':
            counter_bad += 1
        else:
            counter_good +=1

        print(f'''{counter}/480 PROCESSED EIS 
              {counter_good}/480 GOOD FITS
              {counter_bad}/480 BAD FITS
              {counter_fail}/480 FAILED FITS''')




#%% [markdown]
# ## Summary aggregation
# This final section merges mass transfer, thickness, digestion, and EIS results into a single summary table.
# The consolidated file captures recipe-level performance across all experiments.

#%% summary all
df_summary = df_summary_ft.copy()
for log in df_summary.Log.unique():

    df_log_recipe_rt = df_summary_rt.where(df_summary_rt.Log==log).dropna(how='all').copy()
    for well in df_log_recipe_rt.Well.unique():
        well_row = well[0]
        idx = df_log_recipe_rt['Well'].str.contains(well_row,na=False)
        df_recipe_rt = df_log_recipe_rt[idx].copy().set_index('reagent')    
        recipes_idx = df_summary.where((df_summary.Log == log) & (df_summary.Well.str.contains(well_row))).dropna(how='all').index  
        df_summary.loc[recipes_idx, f'{df_recipe_rt.index[0]} transfer error'] = df_recipe_rt.loc[df_recipe_rt.index[0],'%error']
        df_summary.loc[recipes_idx, f'{df_recipe_rt.index[1]} transfer error'] = df_recipe_rt.loc[df_recipe_rt.index[1],'%error']

    recipes_idx = df_summary.where(df_summary.Log==log).dropna(how='all').index
    
    df_log_recipe_thickness = df_summary_t.where(df_summary_t.Log==log).dropna(how='all').copy()
    df_summary.loc[recipes_idx, 'Electrolyte Thickness Automated'] = df_log_recipe_thickness['Electrolyte Thickness High Boundary'].values
    df_summary.loc[recipes_idx, 'Electrolyte Thickness Manual'] = df_log_recipe_thickness['Electrolyte Thickness'].values
    
    df_log_recipe_digestion = df_summary_d.where(df_summary_d.Log==log).dropna(how='all').copy()    
    df_summary.loc[recipes_idx, 'Electrolyte initial'] = df_log_recipe_digestion['Electrolyte initial'].values
    df_summary.loc[recipes_idx, 'Electrolyte final'] = df_log_recipe_digestion['Electrolyte final'].values
    df_summary.loc[recipes_idx, 'Mass Loss'] = df_log_recipe_digestion['Electrolyte initial'].values - df_log_recipe_digestion['Electrolyte final'].values
    
    df_log_recipe_eis = eis_summary_df.where(eis_summary_df.log==log).dropna(how='all').copy()    
    for well in df_log_recipe_eis.well.unique():
        idx = df_log_recipe_eis['well'].str.contains(well,na=False)
        df_recipe_eis = df_log_recipe_eis[idx].copy().set_index('strain')    
        recipes_idx = df_summary.where((df_summary.Log == log) & (df_summary.Well.str.contains(well))).dropna(how='all').index  
        for strain in df_recipe_eis.index:
            df_summary.loc[recipes_idx, f'EIS parameters strain {strain}'] = str(df_recipe_eis.loc[strain,'parameters'])
            df_summary.loc[recipes_idx, f'EIS chi_value strain {strain}'] = df_recipe_eis.loc[strain,'chi_value']
            df_summary.loc[recipes_idx, f'EIS chi_value_HF strain {strain}'] = df_recipe_eis.loc[strain,'chi_value_HF']
            df_summary.loc[recipes_idx, f'EIS fitting outcome {strain}'] = df_recipe_eis.loc[strain,'outcome']
df_summary.to_csv(main_dir + r'\summary.csv', index=False)



