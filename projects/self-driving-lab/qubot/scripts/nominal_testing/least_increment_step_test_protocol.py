# -*- coding: utf-8 -*-
"""
Created on Wed Jan  8 12:34:20 2025

@author: jjcheng3
"""

#%% [markdown]
# # Least Increment Step Test Protocol

# This script implements a least increment step test protocol for evaluating the minimum reliable step size of a robotic positioning system. The test determines the smallest movement increment that the system can consistently execute.

# Overview

# The test protocol involves:
# 1. Connecting to the device under test (robotic system)
# 2. Homing the device to establish reference coordinates
# 3. Moving to a starting test position
# 4. Performing incremental movements in decreasing step sizes away from the reference
# 5. Performing incremental movements in increasing step sizes back to the reference

# This script needs to be run concurrently with the data_acquisition.py script to capture position data during the test for analysis.
#%% [markdown]
# ## Import Required Libraries

#%% IMPORTS
import serial.tools.list_ports
import time
import numpy as np

#%% [markdown]
# ## Connect to Gauge and Device Under Test
# Establish serial communication with the device under test.
# Note: Add correct COM port for device under test and gauge before running.

#%%
# Print available ports
ports = serial.tools.list_ports.comports()

for port, desc, hwid in sorted(ports):
        print("{}: {} [{}]".format(port, desc, hwid))


#%%
# Connect to device under test

import os
DEVICE_PORT = os.environ.get('DEVICE_PORT', '')  # e.g. 'COM4' or '/dev/ttyUSB1' (GRBL, 115200 baud)
device = serial.Serial(DEVICE_PORT, 115200) # Update with correct COM port (or set DEVICE_PORT)
device.flushInput()

time.sleep(2)

# Home device
device.write(bytes("$H\n", 'utf-8'))
print(device.readline())


#%% [markdown]
# ## Move to Test Position for Zero Calibration

# Position the device at the starting location for the least increment step test. This establishes the reference point from which incremental movements will be made.

# - Test position: X=140, Y=-90 (X-axis under test)
# - Command: G90 (absolute positioning) followed by G0 (rapid move)
# - Purpose: Establish consistent starting position for the step test
# Note: Uncomment the Y-axis commands if testing Y-axis repeatability instead.

#%% Go to test position for zero calib

testpos = 140

device.write(bytes("G90\n", 'utf-8'))
print(device.readline())

# X-axis under test
device.write(bytes("G0 X" + str(testpos) + "Y90\n",'utf-8'))
print(device.readline())

# Y-axis under test
# qubot.write(bytes("G0 X70 Y" + str(testpos) + "\n",'utf-8'))
# print(qubot.readline())

#%% [markdown]
# ## Execute Least Increment Step Test

# Run the main test procedure that evaluates the device's ability to execute precise, small movements. The test consists of two phases:

# Phase 1: Decreasing Steps (Moving Away from Reference)
# - Start at test position (X=140)
# - Move in 11 steps of decreasing size (step = 0.100 units)
# - Each step moves further from the reference position
# - Position = testpos - i × step (where i ranges from 0 to 10)

# Phase 2: Increasing Steps (Moving Back to Reference)
# - Continue from the final position of Phase 1
# - Move in 11 steps of increasing size back toward reference
# - Position = current_pos + i × step (where i ranges from 0 to 10)

# Test Parameters:
# - Step size: 0.100 units can be adjusted based on tested precision
# - Number of steps per phase: 11 (i = 0 to 10)
# - Axis under test: X-axis
# - Y position: fixed at -90
# - Movement command: G0 (rapid positioning)
# - Settling time: 10 seconds per step

# Purpose: Evaluate the minimum reliable movement increment the system can achieve.
# Note: Uncomment the Y-axis commands if testing Y-axis repeatability instead. Please ensure that the data acquisition script is running concurrently to capture position data for analysis during the test.

#%% Start test

step = 0.100

for i in np.arange(11):
    print(i)

    device.write(bytes("G90\n", 'utf-8'))
    
    # X-axis under test
    device.write(bytes("G0 X" + str(testpos - i * step) + "Y-90\n", 'utf-8'))
    
    # Y-axis under test
    # device.write(bytes("G0 X70 Y" + str(testpos - i * step) + "\n",'utf-8'))
    
    print(testpos - i * step)
    
    time.sleep(10)
    
#%% Phase 2: Increasing Steps (Return Movement)

testpos = testpos - i * step
    
for i in np.arange(11):
    print(i)

    device.write(bytes("G90\n", 'utf-8'))
    
    # X-axis under test
    device.write(bytes("G0 X" + str(testpos + i * step) + "Y-90\n", 'utf-8'))
    
    # Y-axis under test
    # device.write(bytes("G0 X70 Y" + str(testpos + i * step) + "\n",'utf-8'))
    
    print(testpos + i * step)
    
    time.sleep(10)

