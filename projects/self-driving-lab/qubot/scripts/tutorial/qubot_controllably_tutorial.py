# %% [markdown]
## Gantry Tutorial for Qubot Operation
### Objective
# This tutorial shows how to initialize, inspect, and move a Cartesian Gantry robot.
# It focuses only on the Gantry class and the basic workflow needed for day-to-day use.

# %% [markdown]
### Gantry class
# The Gantry class controls Cartesian robots that move along x, y, and z axes.
# These robots are typically connected through a serial port and may require a home step before accurate moves.

# %% [markdown]
#### Initialization
# Use the correct COM port and motion controller type when creating the robot.
# Common controller names are `GRBL` for Arduino Nano systems and `RepRap` for Duet-based systems.

# %%
from controllably.Move.Cartesian import Gantry

cartesian = Gantry('COM_PORT', device_type_name='GRBL')
cartesian.disconnect()

# %% [markdown]
#### Initialization with workspace settings
# Optional settings let you define motion limits, tool offset, calibrated workspace offset, and a safe Z height.
# These values are useful when the Gantry is operating over a deck or other fixed workspace.

# %%
from controllably.Move.Cartesian import Gantry
import numpy as np

limits = ((0, -498.8, -195.5), (186, 0, 0))
calibrated_offset = np.array([[-205.5, 465.8, 201.3], [-90, 0, 0]])  # translation, then rotation
tool_offset = np.array([[-5, 0, 0]])
safe_height = -1  # safe Z position used by safeMoveTo

cartesian = Gantry(
    'COM_PORT',
    device_type_name='GRBL',
    limits=limits,
    tool_offset=tool_offset,
    calibrated_offset=calibrated_offset,
    safe_height=safe_height,
)

# %% [markdown]
#### Position properties
# These properties report the Gantry location in robot coordinates or workspace coordinates.
# Use workspace coordinates when the robot has been calibrated to a deck or fixture.

# %%
rcoord = cartesian.robot_position      # robot coordinates from the controller
recoord = cartesian.tool_position      # tool position in robot coordinates
wcoord = cartesian.work_position       # robot position in workspace coordinates
pcoord = cartesian.position            # alias for workspace position
wecoord = cartesian.worktool_position  # tool position in workspace coordinates

print(f"""Robot coordinates: {rcoord}
Robot tool coordinates: {recoord}
Workspace coordinates: {wcoord}
Position alias: {pcoord}
Workspace tool coordinates: {wecoord}
""")

# %% [markdown]
#### Speed properties
# Speed settings let you read the current speed and scale the motion speed during operation.
# `speed_factor` is commonly used to slow the robot down during setup or testing.

# %%
speed = cartesian.speed
speed_max = cartesian.speed_max
speed_factor = cartesian.speed_factor

print(f"""Robot speed: {speed} mm/s
Maximum speed: {speed_max} mm/s
Speed factor: {speed_factor}
""")

cartesian.speed_factor(0.5)  # reduce speed to 50% of the current maximum

print(f"Updated speed: {cartesian.speed} mm/s")
print(f"Updated speed factor: {cartesian.speed_factor}")

cartesian.speed_factor(speed_factor)  # restore the original speed factor

# %% [markdown]
#### Main movement methods
# `home` returns the robot to its home position.
# `move` performs a relative move along one axis.
# `moveTo` performs an absolute move, and `safeMoveTo` lifts to the safe height before moving laterally.

# %%
cartesian.home()  # home the robot
cartesian.move('x', 10)  # move 10 mm along X

# Replace the example coordinates below with values that are safe for your setup.
# cartesian.moveTo((0, 0, 0))
# cartesian.safeMoveTo((0, 0, 0))

# %% [markdown]
#### Typical workflow
# A common workflow is:
# 1. Connect and initialize the Gantry.
# 2. Home the robot.
# 3. Check the current position.
# 4. Move with `move`, `moveTo`, or `safeMoveTo`.
# 5. Disconnect when finished.

# %%
print("Current workspace position:", cartesian.position)

# %% [markdown]
#### Shutdown
# Disconnect the Gantry when the session is complete to close the serial connection cleanly.

# %%
cartesian.disconnect()
