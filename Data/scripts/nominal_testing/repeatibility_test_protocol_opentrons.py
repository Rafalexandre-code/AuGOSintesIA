# %% [markdown]
# # Repeatability test of OT-2 gantry
# This notebook contains the code to test the repeatability in the XY space of the OT2 OT-2 robot. 
# The notebook contains two seperate versions of the test depending if the X or Y axis is being tested. 
# In parallel a data_acquisition.py is run in another kernel to read the values from a Mitutoyo s112xb2 position gage. 

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
# ## X-axis test positive
# The OT2 will be positioned a the location of the gauge. 
# The gage will zero using data_acquisition.py. 
# When the gage is zeroed and streaming the data the second cell should be run using data. 
# The command of this cell will make the OT-2 move to a random distance from the gauge in the x-axis and return to the starting position that has been set as zero. 

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
#Start repeatability experiment
input('Safety check')

df= pd.DataFrame(columns=['Time at gage','Target coordinate','Random x coordinate'])

for i in range(50):
    x_r = random.random()*(x_h-x_t) + x_t
    random_loc = Location(Point(x_r,y_t,z_t),None)
    diff = random_loc.point - target_loc.point
    if diff.x < 0:
        print('Risk of collsion')
        break
    elif diff.x> x_h:
        print('Risk of collsion')
        break
    else:
        pipette300.move_to(random_loc)
        time.sleep(3)
        pipette300.move_to(target_loc)
        timestamp = datetime.datetime.now()
        time.sleep(5)
        df.loc[i]={'Time at gage':timestamp,'Target coordinate':f'{x_t},{y_t},{z_t}','Random x coordinate':x_r}
    print(f'Repeat test number:{i}')

df.to_csv('positive_OT2_X_2.csv',index=False)

# %% [markdown]
# ## X-axis test negative
# The OT2 will be positioned a the location of the gauge. 
# The gage will zero using data_acquisition.py. 
# When the gage is zeroed and streaming the data the second cell should be run using data. 
# The command of this cell will make the OT-2 move to a random disance from the gauge in the x-axis and return to the starting position that has been set as zero. 

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

pipette300.move_to(Location(Point(x_h-410,y_h,z_t), None))
pipette300.move_to(Location(Point(x_h-410,y_t,z_t), None))


input('Place the gauge in')



# %%
#Start repeatability experiment
input('Safety check')

df= pd.DataFrame(columns=['Time at gage','Target coordinate','Random x coordinate'])

for i in range(100):
    x_r = x_t  - random.random()*(x_t- (x_h-410))
    random_loc = Location(Point(x_r,y_t,z_t),None)
    diff = random_loc.point - target_loc.point
    if diff.x > 0:
        print('Risk of collsion with gage')
        break
    elif x_r < x_h-410:
        print('Risk of collsion with gantry')
        break
    else:
        pipette300.move_to(random_loc)
        time.sleep(3)
        pipette300.move_to(target_loc)
        timestamp = datetime.datetime.now()
        time.sleep(5)
        df.loc[i]={'Time at gage':timestamp,'Target coordinate':f'{x_t},{y_t},{z_t}','Random x coordinate':x_r}
    print(f'Repeat test number:{i}')

df.to_csv('negative_OT2_X.csv',index=False)

# %% [markdown]
# ## Y-axis test positive
# The OT2 will be positioned a the location of the gauge. 
# The gage will zero using data_acquisition.py. 
# When the gage is zeroed and streaming the data the second cell should be run using data. 
# The command of this cell will make the OT-2 move to a random distance from the gauge in the y-axis and return to the starting position that has been set as zero. 

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

pipette300.move_to(Location(Point(x_t,y_h,z_t), None))


input('Place the gauge in')



# %%
#Start repeatability experiment
input('Safety check')

df= pd.DataFrame(columns=['Time at gage','Target coordinate','Random y coordinate'])

for i in range(100):
    y_r = random.random()*(y_h-y_t)+y_t
    random_loc = Location(Point(x_t,y_r,z_t),None)
    diff = random_loc.point - target_loc.point
    if diff.y < 0:
        print('Risk of collsion')
        break
    elif diff.y > y_h:
        print('Risk of collsion')
        break
    else:
        pipette300.move_to(random_loc)
        time.sleep(3)
        pipette300.move_to(target_loc)
        timestamp = datetime.datetime.now()
        time.sleep(5)
        df.loc[i]={'Time at gage':timestamp,'Target coordinate':f'{x_t},{y_t},{z_t}','Random y coordinate':y_r}
    print(f'Repeat test number:{i}')

df.to_csv('positive_OT2_Y.csv',index=False)

# %% [markdown]
# ## Y-axis test negative
# The OT2 will be positioned a the location of the gauge. 
# The gage will zero using data_acquisition.py. 
# When the gage is zeroed and streaming the data the second cell should be run using data. 
# The command of this cell will make the OT-2 move to a random distance from the gauge in the y-axis and return to the starting position that has been set as zero. 
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

pipette300.move_to(Location(Point(x_h,y_h-347.50,z_t), None))
pipette300.move_to(Location(Point(x_t,y_h-347.50,z_t), None))
pipette300.move_to(target_loc, None)


input('Place the gauge in')



# %%
#Start repeatability experiment
input('Safety check')

df= pd.DataFrame(columns=['Time at gage','Target coordinate','Random y coordinate'])

for i in range(100):
    y_r = y_t  - random.random()*(y_t- (y_h-347.50))
    random_loc = Location(Point(x_t,y_r,z_t),None)
    diff = random_loc.point - target_loc.point
    if diff.y > 0:
        print('Risk of collsion')
        break
    elif y_r < y_h-347.50:
        print('Risk of collsion')
        break
    else:
        pipette300.move_to(random_loc)
        time.sleep(3)
        pipette300.move_to(target_loc)
        timestamp = datetime.datetime.now()
        time.sleep(5)
        df.loc[i]={'Time at gage':timestamp,'Target coordinate':f'{x_t},{y_t},{z_t}','Random y coordinate':y_r}
    print(f'Repeat test number:{i}')

df.to_csv('negative_OT2_Y.csv',index=False)
