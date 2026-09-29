# main_script.py

import os
import time
from math import cos, pi, sin

import numpy as np
from ase import Atoms
from ase.build import graphene_nanoribbon
from ase.io import read, write
from generate_GO import build


# Define a function to run the functionalization process
def run_functionalization(
    input_structure,
    O_content,
    OH_ratio,
    disorder,
    p6,
    edges,
    p4,
    funct_groups,
    vacuum,
    max_iterations,
    output_structure,
):
    # Create an instance of the build class
    build_instance = build()
    # Call the main function from the build class
    build_instance.main(
        input_structure,
        O_content,
        OH_ratio,
        disorder,
        p6,
        edges,
        p4,
        funct_groups,
        vacuum,
        max_iterations,
        output_structure,
    )


# Is the structure disordered?
disorder = True

# Are the edges functionalized?
edges = False

# Enter range of O_content, OH_fraction and p6 values to be used
O_content_range = np.arange(0.1, 0.35, 0.05)
# O_content_range = [0.15]
# OH_fraction_range = np.arange(0.0, 1.25, 0.25)
OH_fraction_range = [0.5]
if disorder:

    def powspace(start, stop, power, num):
        start = np.power(start, 1 / float(power))
        stop = np.power(stop, 1 / float(power))
        return np.power(np.linspace(start, stop, num=num), power)

    # p6_range = [0.7]
    p6_range = powspace(0.3, 0.8, 2, 5)
    print(p6_range)
else:
    p6_range = [1]
if edges:
    # p4_range = [1]
    p4_range = np.arange(0.1, 0.6, 0.1)
else:
    p4_range = [0]

# Generate carboxyl group centered at (0,0,0)
carboxyl = Atoms("COOH", positions=[(0, 0, 0), (0, 1, 0), (0, 0, 1), (1, 0, 0)])
carboxyl.set_positions(
    [
        (0, 0, 0),
        (sin(5 * pi / 6) * 1.21, 0, cos(5 * pi / 6) * 1.21),
        (sin(pi / 6) * 1.30, 0, cos(pi / 6) * 1.30),
        (
            sin(pi / 6) * 1.30 + sin(pi / 2) * 0.96,
            0,
            cos(pi / 6) * 1.30 + cos(pi / 2) * 0.96,
        ),
    ]
)
# Generate aldehyde group centered at (0,0,0) - approx bond angle 120
aldehyde = Atoms("CHO", positions=[(0, 0, 0), (0, 1, 0), (0, 0, 1)])
aldehyde.set_positions(
    [
        (0, 0, 0),
        (sin(5 * pi / 6) * 1.09, 0, cos(5 * pi / 6) * 1.09),
        (sin(pi / 6) * 1.20, 0, cos(pi / 6) * 1.20),
    ]
)
# Generate OH group centered at (0,0,0)
hydroxyl = Atoms("OH", positions=[(0, 0, 0), (0, 1, 0)])
hydroxyl.set_positions([(0, 0, 0), (sin(pi / 6) * 0.96, 0, cos(pi / 6) * 0.96)])

# Tuple containing the functional groups for edge functionalisation
funct_groups = (carboxyl, aldehyde, hydroxyl)

# Store value of vacuum along direction of edges
vacuum = 10

if disorder:
    # Path to input structure
    # The paper's database (../structures/aG_p6.xyz) is not distributed. Set GO_AMORPHOUS_DB to your own
    # file, or build a surrogate with `python make_amorphous_db.py` (-> ../structures/aG_p6_surrogate.xyz).
    input_strucuture = os.environ.get("GO_AMORPHOUS_DB", "../structures/aG_p6.xyz")
    if not os.path.exists(input_strucuture) and os.path.exists("../structures/aG_p6_surrogate.xyz"):
        print("aG_p6.xyz not found: using the SURROGATE database ../structures/aG_p6_surrogate.xyz")
        input_strucuture = "../structures/aG_p6_surrogate.xyz"
    print("Reading amorphous database")
    graphene_init = read(input_strucuture, index=":")
    graphene = graphene_init.copy()

elif edges:
    # Create saturated 1D ribbon
    graphene_init = graphene_nanoribbon(
        7, 5, type="armchair", saturated=True, sheet=False, vacuum=vacuum
    )

else:
    # Create pristine 2D graphene
    graphene_init = graphene_nanoribbon(
        7, 5, type="armchair", saturated=False, sheet=True, vacuum=vacuum
    )

for j in range(20):
    for O_content in O_content_range:
        for OH_fraction in OH_fraction_range:
            for p6 in p6_range:
                for p4 in p4_range:
                    if not disorder:
                        # We need a copy of initial structure to avoid oxidising the same strucuture twice.
                        graphene = graphene_init.copy()
                    # Define the output structure name
                    output_structure = f"../inital_configs/p1-p4/batch-{j}/GO-{O_content:.2f}-{p6:.2f}.xyz".format(
                        O_content, OH_fraction
                    )
                    os.makedirs(os.path.dirname(output_structure), exist_ok=True)
                    # Run the functionalization process
                    run_functionalization(
                        graphene,
                        O_content,
                        OH_fraction,
                        disorder,
                        p6,
                        edges,
                        p4,
                        funct_groups,
                        vacuum,
                        200,
                        output_structure,
                    )
