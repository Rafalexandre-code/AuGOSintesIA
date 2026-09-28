# -*- coding: utf-8 -*-
"""
Created on Wed Jan  8 12:34:20 2025

@author: jjcheng3
"""
#%% [markdown]
# # Repeatability Test Protocol

# This notebook implements a repeatability test protocol for evaluating the precision of a robotic positioning system. The test measures how consistently the system can return to a reference position after moving to various random positions.

## Overview

# The test protocol involves:
# 1. Connecting to measurement equipment (Mitutoyo gauge)
# 2. Connecting to the device under test (robotic system)
# 3. Homing the device
# 4. Establishing a reference position
# 5. Performing repeated movements to random positions and measuring return accuracy
# 6. Collecting and analyzing the measurement data

#%%
## Import Required Libraries

# Import the necessary Python libraries for serial communication, timing, random number generation, numerical operations, and data handling.
#%% IMPORTS
import serial
import serial.tools.list_ports
import time
import random
import numpy as np
import pandas as pd
#%% [markdown]
# # Connect to Gauge and Device Under Test
# Establish serial communication with the Mitutoyo digital gauge. This device will measure the position accuracy during the repeatability test.
# Note: Add correct COM port for device under test and gauge before running.

#%%
ports = serial.tools.list_ports.comports()

for port, desc, hwid in sorted(ports):
        print("{}: {} [{}]".format(port, desc, hwid))

#%% Connect to Mitutoyo gauge

gauge = serial.Serial('', 2400) # Update with correct COM port
time.sleep(2)


#%% Connect to device under test

device = serial.Serial('', 115200) # Update with correct COM port
device.flushInput()

time.sleep(2)

device.write(bytes("$H\n", 'utf-8'))
print(device.readline())

#%%
# ## Move to Test Position for Zero Calibration

# Position the device at the reference location where measurements will be taken. This establishes the "zero" or reference point for the repeatability test.

# - Test position: X=140, Y=90 (X-axis under test)
# - Command: G90 (absolute positioning) followed by G0 (rapid move)
# - Purpose: Establish consistent reference position for measurements
# Note: Uncomment the Y-axis commands if testing Y-axis repeatability instead.
#%%

device.write(bytes("$H\n", 'utf-8'))
print(device.readline())

#%% Go to test position for zero calib 

xtestpos = 140 # Input test position for X-axis under test
ytestpos = 90 # Input test position for Y-axis under test
device.write(bytes("G90\n", 'utf-8'))
print(device.readline())

# UNCOMMENT/COMMENT TO SELECT AXIS UNDER TEST 
# X-axis under test
device.write(bytes("G0 X" + str(xtestpos) + "Y" + str(ytestpos) + "\n",'utf-8'))
print(device.readline())

# Y-axis under test
# device.write(bytes("G0 X" + str(xtestpos) + " Y" + str(ytestpos) + "\n",'utf-8'))
# print(device.readline())

#%% [markdown]
# ## Execute Repeatability Test

# Run the main test loop that evaluates positioning repeatability. The test procedure:

# 1. Generate a random starting position within the test range
# 2. Move to the random position
# 3. Return to the reference position (testpos)
# 4. Take a measurement with the Mitutoyo gauge
# 5. Record the data and repeat

# Test Parameters:
# - Number of iterations: 50
# - Test range: testpos+20 to axismax (160 to 280)
# - Axis under test: X-axis
# - Measurement: Position error at reference location
# - Output: CSV file with index, start position, and gauge reading

# Data Analysis:
# - Standard deviation of measurements indicates repeatability
# - Lower standard deviation = better repeatability
# Note: Uncomment the Y-axis commands if testing Y-axis repeatability instead.

#%% Start test

data = pd.DataFrame(columns = ['Index','Start Position', 'Gauge'])
direction = '+' # Set direction for random start position generation
axismax = 280 # Maximum position for random start (adjust based on device limits)

for i in np.arange(50):
    print(i)
    
    startpos = random.randint(xtestpos + 20, axismax) # Change depending direction of test
    print(startpos)

    device.write(bytes("G90\n", 'utf-8'))
    
    # X-axis under test
    device.write(bytes("G0 X" + str(startpos) + "Y" + str(ytestpos) + "\n", 'utf-8'))
    
    # Y-axis under test
    # device.write(bytes("G0 X" + str(xtestpos) + " Y" + str(startpos) + "\n",'utf-8'))
    
    time.sleep(9)
    
    device.write(bytes("G90\n", 'utf-8'))
    
    # X-axis under test
    device.write(bytes("G0 X" + str(xtestpos) + "Y" + str(ytestpos) + "\n", 'utf-8'))
    
    # Y-axis under test
    # device.write(bytes("G0 X" + str(xtestpos) + " Y" + str(ytestpos) + "\n",'utf-8'))
    
    time.sleep(14)
    
    gauge.write(bytes("1\r", 'utf-8'))
    reading = gauge.read_until(b'\r')
    print(reading)

    data.loc[len(data.index)] = [i, startpos, float(reading[-7:-1])]
    
    print(data.std())
    
data.to_csv(f'X Repeatability X{xtestpos} Y{ytestpos} {direction}ve.csv')


# %%
