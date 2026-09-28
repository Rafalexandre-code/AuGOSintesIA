# %% [markdown]
# # Least increment step test of OT-2 gantry
# This notebook contains the code to test the least increment step in the XY space of the OT2 OT-2 robot. 
# The notebook contains two seperate versions of the test depending if the X or Y axis is being tested. 
# In parallel data_acquisition.py is run in another kernel to read the values from a Mitutoyo s112xb2 position gage. 

#%% [markdown]
# ## Importing libraries and initializing the OT-2
# %%
import serial.tools.list_ports

comlist = serial.tools.list_ports.comports()
for port in comlist:
    print(port.device)#Imports
import time
import OT2.execute
import datetime
import random
from OT2.types import Location, Point, Mount
import pandas as pd

# %%
#initialize opentron control
protocol = OT2.execute.get_protocol_api('2.11')
protocol.home()
pipette300 = protocol.load_instrument('p300_multi_gen2', 'right')


# print bounds of the gantry to make sure the random coordinates are within the limits of the robot
print(protocol._implementation._sync_hardware._backend.axis_bounds)


# %% [markdown]
# ## Y-axis test ladder test
# The OT2 will be positioned a the location of the gage. 
# The gage will zero using data_acquisition.py. 
# When the gage is zeroed and streaming the data the second cell should be run. 
# The command of this cell will make the OT-2 move in a predefined distance  <0.100 mm for ten times. 

# %%
#Move OT2 close to the Gage to take zero position
input('Safety check')

protocol.home()
home_loc = protocol._hw_manager.hardware.gantry_position(Mount(2))
x_h,y_h,z_h = home_loc

x_t = x_h - 411.74/2
y_t = y_h - 347.50/2
z_t = z_h - 50


target_loc = Location(Point(x_t,y_t
                            ,z_t),None)

pipette300.move_to(Location(Point(x_h,y_h-347.50,z_t), None))
pipette300.move_to(Location(Point(x_t,y_h-347.50,z_t), None))
pipette300.move_to(target_loc, None)


input('Place the gauge in')


# %%
input('Safety check')

pipette300.move_to(target_loc, None)
step_size = 0.01
for i in range(1,11):
    next_y = y_t+i*step_size
    print(next_y)
    new_loc = Location(Point(x_t,next_y,z_t),None)
    pipette300.move_to(new_loc, None)
    time.sleep(10)

last_y = next_y

for i in range(1,11):
    next_y = last_y-i*step_size
    print(next_y)
    new_loc = Location(Point(x_t,next_y,z_t),None)
    pipette300.move_to(new_loc, None)
    time.sleep(10)

# %%
#Home back to reset measurment
input('Safety check')

pipette300.move_to(Location(Point(x_t,y_h-347.50,z_t), None))
pipette300.move_to(Location(Point(x_h,y_h-347.50,z_t), None))
protocol.home()


# %% [markdown]
# ## X-axis test ladder test
# The OT2 will be positioned a the location of the gage. 
# The gage will zero using data_acquisition.py.
# When the gage is zeroed and streaming the data the second cell should be run. 
# The command of this cell will make the OT-2 move in a predefined distance  <0.100 mm for ten times. 
# %%
#Move OT2 close to the Gage to take zero position
input('Safety check')

protocol.home()
home_loc = protocol._hw_manager.hardware.gantry_position(Mount(2))
x_h,y_h,z_h = home_loc

x_t = x_h - 411.74/2
y_t = y_h - 347.50/2
z_t = z_h - 50


target_loc = Location(Point(x_t,y_t,z_t),None)

pipette300.move_to(Location(Point(x_h,y_t,z_t), None))
pipette300.move_to(target_loc, None)


input('Place the gauge in')




# %%
input('Safety check')

pipette300.move_to(target_loc, None)
step_size = 0.01
for i in range(1,11):
    next_x = x_t-i*step_size
    print(next_x)
    new_loc = Location(Point(next_x,y_t,z_t),None)
    pipette300.move_to(new_loc, None)
    time.sleep(10)

last_x = next_x

for i in range(1,11):
    next_x = last_x+i*step_size
    print(next_x)
    new_loc = Location(Point(next_x,y_t,z_t),None)
    pipette300.move_to(new_loc, None)
    time.sleep(10)

# %%
#Home back to reset measurment
input('Safety check')
pipette300.move_to(Location(Point(x_h,y_t,z_t), None))
protocol.home()



