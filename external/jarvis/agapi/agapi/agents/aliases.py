PROPERTY_ALIASES = {
    # ==================== BANDGAP ====================
    "bandgap": "mbj_bandgap",
    "band gap": "mbj_bandgap",
    "band-gap": "mbj_bandgap",
    "gap": "mbj_bandgap",
    "bg": "mbj_bandgap",
    "electronic bandgap": "optb88vdw_bandgap",
    "optb88vdw bandgap": "optb88vdw_bandgap",
    "optb88vdw_bandgap": "optb88vdw_bandgap",
    # MBJ bandgap
    "mbj bandgap": "mbj_bandgap",
    "mbj_bandgap": "mbj_bandgap",
    "mbj gap": "mbj_bandgap",
    "mbj": "mbj_bandgap",
    # HSE bandgap
    "hse bandgap": "hse_gap",
    "hse_gap": "hse_gap",
    "hse gap": "hse_gap",
    "hse": "hse_gap",
    # ==================== ENERGY ====================
    # Formation energy
    "formation energy": "formation_energy_peratom",
    "formation_energy": "formation_energy_peratom",
    "hf": "formation_energy_peratom",
    "e_form": "formation_energy_peratom",
    "formation": "formation_energy_peratom",
    "form energy": "formation_energy_peratom",
    "form_energy": "formation_energy_peratom",
    # Total energy
    "total energy": "optb88vdw_total_energy",
    "optb88vdw_total_energy": "optb88vdw_total_energy",
    "total_energy": "optb88vdw_total_energy",
    # Energy above hull (stability)
    "ehull": "ehull",
    "energy above hull": "ehull",
    "hull energy": "ehull",
    "stability": "ehull",
    "e_hull": "ehull",
    "above hull": "ehull",
    # ==================== MECHANICAL PROPERTIES ====================
    # Bulk modulus
    "bulk modulus": "bulk_modulus_kv",
    "bulk_modulus": "bulk_modulus_kv",
    "k": "bulk_modulus_kv",
    "kv": "bulk_modulus_kv",
    "stiffness": "bulk_modulus_kv",
    "modulus": "bulk_modulus_kv",
    "bulk_modulus_kv": "bulk_modulus_kv",
    # Shear modulus
    "shear modulus": "shear_modulus_gv",
    "shear_modulus": "shear_modulus_gv",
    "g": "shear_modulus_gv",
    "gv": "shear_modulus_gv",
    "shear_modulus_gv": "shear_modulus_gv",
    # Poisson ratio
    "poisson": "poisson",
    "poisson ratio": "poisson",
    "poisson_ratio": "poisson",
    # Density
    "density": "density",
    "rho": "density",
    "mass density": "density",
    # Elastic tensor
    "elastic tensor": "elastic_tensor",
    "elastic_tensor": "elastic_tensor",
    "elasticity": "elastic_tensor",
    # ==================== MAGNETIC PROPERTIES ====================
    "magnetization": "magmom_oszicar",
    "magnetic moment": "magmom_oszicar",
    "magmom": "magmom_oszicar",
    "magmom_oszicar": "magmom_oszicar",
    "mag moment": "magmom_oszicar",
    "magmom outcar": "magmom_outcar",
    "magmom_outcar": "magmom_outcar",
    # ==================== SUPERCONDUCTIVITY ====================
    "tc": "Tc_supercon",
    "tc_supercon": "Tc_supercon",
    "superconducting temperature": "Tc_supercon",
    "critical temperature": "Tc_supercon",
    "supercon tc": "Tc_supercon",
    "superconductor": "Tc_supercon",
    # ==================== DIELECTRIC PROPERTIES ====================
    # X direction
    "epsx": "epsx",
    "epsilon x": "epsx",
    "dielectric x": "epsx",
    "dielectric constant x": "epsx",
    # Y direction
    "epsy": "epsy",
    "epsilon y": "epsy",
    "dielectric y": "epsy",
    "dielectric constant y": "epsy",
    # Z direction
    "epsz": "epsz",
    "epsilon z": "epsz",
    "dielectric z": "epsz",
    "dielectric constant z": "epsz",
    # Generic dielectric
    "dielectric": "epsx",
    "dielectric constant": "epsx",
    "epsilon": "epsx",
    # Magnetic dielectric
    "mepsx": "mepsx",
    "mepsy": "mepsy",
    "mepsz": "mepsz",
    # ==================== PIEZOELECTRIC PROPERTIES ====================
    "piezoelectric": "dfpt_piezo_max_eij",
    "piezo": "dfpt_piezo_max_eij",
    "dfpt_piezo_max_eij": "dfpt_piezo_max_eij",
    "piezo eij": "dfpt_piezo_max_eij",
    "piezo_eij": "dfpt_piezo_max_eij",
    "dfpt_piezo_max_dij": "dfpt_piezo_max_dij",
    "piezo dij": "dfpt_piezo_max_dij",
    "piezo_dij": "dfpt_piezo_max_dij",
    "piezo dielectric": "dfpt_piezo_max_dielectric",
    "dfpt_piezo_max_dielectric": "dfpt_piezo_max_dielectric",
    "piezo dielectric electronic": "dfpt_piezo_max_dielectric_electronic",
    "dfpt_piezo_max_dielectric_electronic": "dfpt_piezo_max_dielectric_electronic",
    "piezo dielectric ionic": "dfpt_piezo_max_dielectric_ionic",
    "dfpt_piezo_max_dielectric_ionic": "dfpt_piezo_max_dielectric_ionic",
    # ==================== TRANSPORT PROPERTIES ====================
    # Seebeck coefficient
    "n-seebeck": "n-Seebeck",
    "n seebeck": "n-Seebeck",
    "nseebeck": "n-Seebeck",
    "seebeck n": "n-Seebeck",
    "p-seebeck": "p-Seebeck",
    "p seebeck": "p-Seebeck",
    "pseebeck": "p-Seebeck",
    "seebeck p": "p-Seebeck",
    "seebeck": "n-Seebeck",
    "seebeck coefficient": "n-Seebeck",
    # Power factor
    "n-powerfact": "n-powerfact",
    "n powerfact": "n-powerfact",
    "npowerfact": "n-powerfact",
    "power factor n": "n-powerfact",
    "p-powerfact": "p-powerfact",
    "p powerfact": "p-powerfact",
    "ppowerfact": "p-powerfact",
    "power factor p": "p-powerfact",
    "power factor": "n-powerfact",
    "powerfactor": "n-powerfact",
    # Conductivity
    "ncond": "ncond",
    "n conductivity": "ncond",
    "conductivity n": "ncond",
    "pcond": "pcond",
    "p conductivity": "pcond",
    "conductivity p": "pcond",
    "conductivity": "ncond",
    "electrical conductivity": "ncond",
    # Thermal conductivity
    "nkappa": "nkappa",
    "n kappa": "nkappa",
    "thermal conductivity n": "nkappa",
    "pkappa": "pkappa",
    "p kappa": "pkappa",
    "thermal conductivity p": "pkappa",
    "kappa": "nkappa",
    "thermal conductivity": "nkappa",
    # ==================== EFFECTIVE MASSES ====================
    "avg_elec_mass": "avg_elec_mass",
    "average electron mass": "avg_elec_mass",
    "electron mass": "avg_elec_mass",
    "elec mass": "avg_elec_mass",
    "effective electron mass": "avg_elec_mass",
    "avg_hole_mass": "avg_hole_mass",
    "average hole mass": "avg_hole_mass",
    "hole mass": "avg_hole_mass",
    "effective hole mass": "avg_hole_mass",
    "effective_masses_300K": "effective_masses_300K",
    "effective masses": "effective_masses_300K",
    "eff masses": "effective_masses_300K",
    # ==================== SOLAR CELL PROPERTIES ====================
    "slme": "slme",
    "solar efficiency": "slme",
    "spectroscopic limited maximum efficiency": "slme",
    "solar cell efficiency": "slme",
    # ==================== TOPOLOGICAL PROPERTIES ====================
    "spillage": "spillage",
    "topological spillage": "spillage",
    # ==================== ELECTRIC FIELD GRADIENT ====================
    "max_efg": "max_efg",
    "efg": "efg",
    "electric field gradient": "max_efg",
    "field gradient": "max_efg",
    # ==================== INFRARED MODES ====================
    "max_ir_mode": "max_ir_mode",
    "max ir mode": "max_ir_mode",
    "maximum ir mode": "max_ir_mode",
    "min_ir_mode": "min_ir_mode",
    "min ir mode": "min_ir_mode",
    "minimum ir mode": "min_ir_mode",
    "modes": "modes",
    "vibrational modes": "modes",
    "phonon modes": "modes",
    # ==================== EXFOLIATION ====================
    "exfoliation_energy": "exfoliation_energy",
    "exfoliation": "exfoliation_energy",
    "exfoliation energy": "exfoliation_energy",
    "cleavage energy": "exfoliation_energy",
    # ==================== STRUCTURAL PROPERTIES ====================
    # Space group
    "spg": "spg",
    "space group": "spg_symbol",
    "spg_symbol": "spg_symbol",
    "spg symbol": "spg_symbol",
    "spacegroup": "spg_symbol",
    "spg_number": "spg_number",
    "spg number": "spg_number",
    "space group number": "spg_number",
    # Crystal system
    "crystal system": "crys",
    "crys": "crys",
    "crystal": "crys",
    # Number of atoms
    "nat": "nat",
    "number of atoms": "nat",
    "num atoms": "nat",
    "natoms": "nat",
    "n atoms": "nat",
    # Dimensionality
    "dimensionality": "dimensionality",
    "dimension": "dimensionality",
    "dim": "dimensionality",
    # Material type
    "typ": "typ",
    "type": "typ",
    "material type": "typ",
    # Formula
    "formula": "formula",
    "chemical formula": "formula",
    "composition": "formula",
    # Structure
    "atoms": "atoms",
    "structure": "atoms",
    "atomic structure": "atoms",
    # ==================== COMPUTATIONAL PARAMETERS ====================
    # Functional
    "func": "func",
    "functional": "func",
    "exchange correlation": "func",
    "xc functional": "func",
    # Energy cutoff
    "encut": "encut",
    "energy cutoff": "encut",
    "cutoff": "encut",
    "ecut": "encut",
    # K-points
    "kpoint_length_unit": "kpoint_length_unit",
    "kpoint length": "kpoint_length_unit",
    "kpoints": "kpoint_length_unit",
    "k-points": "kpoint_length_unit",
    # Mesh
    "maxdiff_mesh": "maxdiff_mesh",
    "mesh": "maxdiff_mesh",
    "maxdiff_bz": "maxdiff_bz",
    "bz": "maxdiff_bz",
    "brillouin zone": "maxdiff_bz",
    # ==================== DATABASE IDENTIFIERS ====================
    "jid": "jid",
    "jarvis id": "jid",
    "jarvis_id": "jid",
    "id": "jid",
    "icsd": "icsd",
    "icsd id": "icsd",
    # ==================== METADATA ====================
    "reference": "reference",
    "ref": "reference",
    "citation": "reference",
    "xml_data_link": "xml_data_link",
    "xml link": "xml_data_link",
    "data link": "xml_data_link",
    "raw_files": "raw_files",
    "raw files": "raw_files",
    "files": "raw_files",
    "search": "search",
    "elements": "search",
}


def normalize_property_name(prop: str) -> str:
    """Normalize property name to API field name"""
    prop_lower = prop.lower().strip()
    for word in [
        "with",
        "the",
        "materials",
        "find",
        "show",
        "get",
        "have",
        "data",
    ]:
        prop_lower = prop_lower.replace(word, "").strip()
    return PROPERTY_ALIASES.get(prop_lower, prop)
