#%% [markdown]
# # Data Acquisition for Least Increment Step Test Protocol
# This script is designed to be run concurrently with the Least Increment Step Test Protocol script. It captures position data from the Mitutoyo gauge during the incremental movement test for subsequent analysis of repeatability and accuracy.

#%% [markdown]
# ## Import Required Libraries

#%% IMPORTS
import os
import serial
import serial.tools.list_ports
import time
from datetime import datetime
import pandas as pd 

#%% [markdown] 
# ## Connect to Mitutoyo Gauge
# Note: Ensure the correct COM port for the Mitutoyo gauge is specified before running this script.
#%%
# List available serial ports
ports = serial.tools.list_ports.comports()

for port, desc, hwid in sorted(ports):
        print("{}: {} [{}]".format(port, desc, hwid))

#%% Connect to Mitutoyo gauge

GAUGE_PORT = os.environ.get('GAUGE_PORT', '')  # e.g. 'COM3' (Windows) or '/dev/ttyUSB0' (Linux)
if not GAUGE_PORT:
    raise ValueError("Set the Mitutoyo gauge serial port: GAUGE_PORT='COM3' (or edit GAUGE_PORT above).")
gauge = serial.Serial(GAUGE_PORT, 2400)
time.sleep(2)

#%% [markdown]
# ## Data Capture Loop
# This loop continuously reads position data from the Mitutoyo gauge during the test. The captured data is stored in a DataFrame for later analysis. The loop can be stopped manually once the test is complete.
# Note: add name of tested device, tested axis and step size
#%%
device_name = ''
axis = ''
step_size = ''

data = []  # List of [time, gauge reading] rows

# Stop the capture with Ctrl+C (or the "interrupt" button of the notebook/IDE)
try:
    while True:
        now = datetime.now().strftime("%H:%M:%S")
        gauge.write(bytes("1\r", 'utf-8'))
        reading = gauge.read_until(b'\r')
        print(reading)

        data.append([now, float(reading[-7:-1])])
except KeyboardInterrupt:
    print(f"Capture stopped: {len(data)} readings")
#%% Save captured data to CSV file
df = pd.DataFrame(data, columns=['Time', 'Gauge'])  # DataFrame to organize captured data
df.to_csv(f'{device_name} {axis}-ladder{step_size}.csv', index=False)
