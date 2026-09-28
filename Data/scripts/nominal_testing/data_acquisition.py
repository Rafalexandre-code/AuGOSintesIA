#%% [markdown]
# # Data Acquisition for Least Increment Step Test Protocol
# This script is designed to be run concurrently with the Least Increment Step Test Protocol script. It captures position data from the Mitutoyo gauge during the incremental movement test for subsequent analysis of repeatability and accuracy.

#%% [markdown]
# ## Import Required Libraries

#%% IMPORTS
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

gauge = serial.Serial('', 2400) # Update with correct COM port
time.sleep(2)

#%% [markdown]
# ## Data Capture Loop
# This loop continuously reads position data from the Mitutoyo gauge during the test. The captured data is stored in a DataFrame for later analysis. The loop can be stopped manually once the test is complete.
# Note: add name of tested device, tested axis and step size
#%%
device_name = ''
axis = ''
step_size = ''

data = []  # List to store captured data
df = pd.DataFrame(columns=['Time', 'Gauge'])  # DataFrame to organize captured data

while True:
    now = datetime.now().strftime("%H:%M:%S")
    gauge.write(bytes("1\r", 'utf-8'))
    reading = gauge.read_until(b'\r')
    print(reading)

    data.loc[len(data.index)] = [now, float(reading[-7:-1])]
#%% Save captured data to CSV file
data.to_csv(f'{device_name} {axis}-ladder{step_size}.csv', index=False)
