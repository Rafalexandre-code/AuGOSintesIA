# AmberGO
AMBER-compatible graphene oxide models, parameters, and charge sets for simulations. Includes GO structures with varying oxidation levels, AMBER frcmod files, and example workflows for building and running GO systems reproducibly.

---

## Repository Overview

### **Building_AMBER_Compatible_Graphene_Oxide_Tutorial.pdf**  
The main tutorial document guiding users through the full workflow for constructing, cleaning, typing, validating, and finalizing AMBER-compatible GO structures.  
All steps referenced in this README and all supporting files originate from this protocol.

---

## **Data Directory**

### **All_final_models.zip**  
A complete collection of **finalized GO models** described in the supporting manuscript.  
These systems represent simulation-ready structures produced after applying the entire pipeline to multiple graphene-based configurations (variation in oxidation, size, and functional group distribution).

This zip contains **only the final outputs**, suitable for immediate use in molecular dynamics simulations.

### **Example_models_with_intermediate_files.zip**  
A curated set of **example graphene-based systems with every intermediate file** generated while following the tutorial workflow.  
These examples illustrate each stage of the process.

---

## **Tutorial Directory**

### **Tutorial.zip**  
Contains all **scripts, images, and helper utilities** referenced in the tutorial PDF, including:

Modified oxidation scripts used for high-percent functionalization  
VMD Tcl scripts for atom typing, artifact detection, ratio calculation, and visualization  
Python utilities for rebuilding MOL2 substructures  
Figures and images embedded in the tutorial  

These materials support full reproducibility of the workflow.

---

## Getting Started

1. Begin with **Building_AMBER_Compatible_Graphene_Oxide_Tutorial.pdf**.  
2. Use **Example_models_with_intermediate_files.zip** to follow the tutorial step-by-step with real data.  
3. Use **All_final_models.zip** to access the complete set of finalized GO systems described in the manuscript.  
4. Refer to **Tutorial.zip** for scripts required to reproduce or extend the workflow.

---

## Citation

If you use these models, scripts, or workflows, please cite both the associated manuscript and the HierGO method.
[![DOI](https://zenodo.org/badge/1112799294.svg)](https://doi.org/10.5281/zenodo.17863270)
