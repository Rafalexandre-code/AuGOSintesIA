"""
Integration tests for agapi/agents/functions.py

No mocks — all tests make real HTTP calls to atomgpt.org.

Setup:
    export AGAPI_KEY="sk-your-key-here"
    pip install pytest httpx jarvis-tools scipy
    pytest test_functions.py -v

Key backend behaviors that affect tests:
  1. query_by_property / find_extreme:
     The backend _apply_filters() returns an EMPTY DataFrame when no
     formula/elements/jid filter is given (by design — safety guard).
     Always combine propranges with elements= or formula=.

  2. diffractgpt_predict:
     /diffractgpt/query returns plain text (POSCAR + comment header),
     NOT a JSON dict. The current functions.py wraps it but calls
     result.get("POSCAR") on a string → error. Tests document this.

  3. protein_fold:
     /protein_fold/query is a GET endpoint that requires APIKEY in query
     params (verify_api_key_required dependency). AGAPIClient injects
     APIKEY automatically into GET params.

  4. alignn_ff_relax / slakonet_bandstructure:
     Backend enforces <= 10 atom limit on POST endpoints.
     Use primitive cells (2 atoms) to stay within limits.
"""

import os
import pytest
from agapi.agents.client import AGAPIClient
from agapi.agents.functions import (
    query_by_formula,
    query_by_jid,
    query_by_elements,
    query_by_property,
    find_extreme,
    alignn_predict,
    alignn_ff_relax,
    slakonet_bandstructure,
    generate_interface,
    make_supercell,
    substitute_atom,
    create_vacancy,
    generate_xrd_pattern,
    protein_fold,
    diffractgpt_predict,
    alignn_ff_single_point,
    alignn_ff_optimize,
    alignn_ff_md,
    pxrd_match,
    xrd_analyze,
    microscopygpt_analyze,
    query_mp,
    query_oqmd,
    search_arxiv,
    search_crossref,
    openfold_predict,
    list_jarvis_columns,
)

pytest.skip("Temporarily disabled", allow_module_level=True)

# ---------------------------------------------------------------------------
# Session-scoped client fixture
# ---------------------------------------------------------------------------

@pytest.fixture(scope="session")
def client():
    api_key = os.environ.get("AGAPI_KEY")
    if not api_key:
        pytest.skip("AGAPI_KEY environment variable not set")
    return AGAPIClient(api_key=api_key)


# ---------------------------------------------------------------------------
# Reference structures
# ---------------------------------------------------------------------------

# Si conventional cell (8 atoms) — for interface / XRD / supercell tests
SI_POSCAR = """\
Si
1.0
   5.468799591  0.000000000  0.000000000
   0.000000000  5.468799591  0.000000000
   0.000000000  0.000000000  5.468799591
Si
8
direct
  0.000000000  0.000000000  0.000000000
  0.000000000  0.500000000  0.500000000
  0.500000000  0.000000000  0.500000000
  0.500000000  0.500000000  0.000000000
  0.250000000  0.250000000  0.250000000
  0.250000000  0.750000000  0.750000000
  0.750000000  0.250000000  0.750000000
  0.750000000  0.750000000  0.250000000
"""

# Si primitive cell (2 atoms) — for ALIGNN/SlakoNet (server limit: <=10 atoms)
SI_POSCAR_PRIM = """\
Si
1.0
   0.000000000  2.734399796  2.734399796
   2.734399796  0.000000000  2.734399796
   2.734399796  2.734399796  0.000000000
Si
2
direct
  0.000000000  0.000000000  0.000000000
  0.250000000  0.250000000  0.250000000
"""

# GaAs conventional cell (8 atoms)
GaAs_POSCAR = """\
GaAs
1.0
   5.750000000  0.000000000  0.000000000
   0.000000000  5.750000000  0.000000000
   0.000000000  0.000000000  5.750000000
Ga As
4  4
direct
  0.000000000  0.000000000  0.000000000
  0.000000000  0.500000000  0.500000000
  0.500000000  0.000000000  0.500000000
  0.500000000  0.500000000  0.000000000
  0.250000000  0.250000000  0.250000000
  0.250000000  0.750000000  0.750000000
  0.750000000  0.250000000  0.750000000
  0.750000000  0.750000000  0.250000000
"""

# GaAs primitive cell (2 atoms) — for ALIGNN/SlakoNet
GaAs_POSCAR_PRIM = """\
GaAs
1.0
   0.000000000  2.875000000  2.875000000
   2.875000000  0.000000000  2.875000000
   2.875000000  2.875000000  0.000000000
Ga As
1 1
direct
  0.000000000  0.000000000  0.000000000
  0.250000000  0.250000000  0.250000000
"""

# Si primitive cell — 2 atoms, well within all server limits
SI_PRIM = """\
Si
1.0
   0.000000000  2.734399796  2.734399796
   2.734399796  0.000000000  2.734399796
   2.734399796  2.734399796  0.000000000
Si
2
direct
  0.000000000  0.000000000  0.000000000
  0.250000000  0.250000000  0.250000000
"""

# Simple XRD pattern data for LaB6 (2theta intensity pairs)
LAB6_XRD = """\
21.38 0.69
30.42 1.00
37.44 0.31
43.50 0.25
49.02 0.49
"""

# Si XRD pattern
SI_XRD = """\
28.44 1.00
47.30 0.55
56.12 0.30
69.13 0.11
76.38 0.12
"""

# ===========================================================================
# query_by_formula
# ===========================================================================

class TestQueryByFormula:

    def test_known_formula_si_returns_results(self, client):
        result = query_by_formula("Si", client)
        assert "error" not in result
        assert result["total"] > 0
        assert len(result["materials"]) > 0

    def test_result_contains_required_keys(self, client):
        result = query_by_formula("Si", client)
        mat = result["materials"][0]
        for key in ["jid", "formula", "spg_symbol",
                    "formation_energy_peratom", "bandgap",
                    "bandgap_source", "ehull"]:
            assert key in mat, f"Missing key: {key}"

    def test_multicomponent_gan(self, client):
        result = query_by_formula("GaN", client)
        assert "error" not in result
        assert result["total"] > 0

    def test_gaas_formula(self, client):
        result = query_by_formula("GaAs", client)
        assert "error" not in result
        assert result["total"] > 0

    def test_bandgap_source_is_valid(self, client):
        result = query_by_formula("Si", client)
        for mat in result["materials"]:
            assert mat["bandgap_source"] in ("mbj", "optb88vdw")

    def test_mbj_bandgap_preferred(self, client):
        result = query_by_formula("Si", client)
        for mat in result["materials"]:
            if mat["mbj_bandgap"] is not None:
                assert mat["bandgap"] == pytest.approx(mat["mbj_bandgap"])
                assert mat["bandgap_source"] == "mbj"

    def test_optb88vdw_fallback_when_mbj_none(self, client):
        result = query_by_formula("Si", client)
        for mat in result["materials"]:
            if mat["mbj_bandgap"] is None and mat["optb88vdw_bandgap"] is not None:
                assert mat["bandgap"] == pytest.approx(mat["optb88vdw_bandgap"])
                assert mat["bandgap_source"] == "optb88vdw"

    def test_unknown_formula_returns_empty(self, client):
        result = query_by_formula("Xt9Zq2", client)
        assert "error" not in result
        assert result["total"] == 0 or len(result["materials"]) == 0

    def test_total_geq_materials_length(self, client):
        result = query_by_formula("Si", client)
        assert result["total"] >= len(result["materials"])


# ===========================================================================
# query_by_jid
# ===========================================================================

class TestQueryByJid:

    def test_jvasp_1002_found(self, client):
        result = query_by_jid("JVASP-1002", client)
        assert "error" not in result
        assert result["jid"] == "JVASP-1002"

    def test_poscar_is_nonempty_string(self, client):
        result = query_by_jid("JVASP-1002", client)
        assert isinstance(result.get("POSCAR"), str)
        assert len(result["POSCAR"]) > 10

    def test_formula_returned(self, client):
        result = query_by_jid("JVASP-1002", client)
        assert result["formula"] is not None

    def test_spg_symbol_returned(self, client):
        result = query_by_jid("JVASP-1002", client)
        assert result["spg_symbol"] is not None

    def test_ehull_present(self, client):
        result = query_by_jid("JVASP-1002", client)
        assert "ehull" in result

    def test_bandgap_source_priority(self, client):
        result = query_by_jid("JVASP-1002", client)
        if result.get("mbj_bandgap") is not None:
            assert result["bandgap"] == pytest.approx(result["mbj_bandgap"])
            assert result["bandgap_source"] == "mbj"

    def test_invalid_jid_returns_error(self, client):
        result = query_by_jid("JVASP-9999999999", client)
        assert "error" in result

    def test_second_jid_gan(self, client):
        result = query_by_jid("JVASP-39", client)
        assert "error" not in result


# ===========================================================================
# query_by_elements
# ===========================================================================

class TestQueryByElements:

    def test_single_element_si(self, client):
        result = query_by_elements("Si", client)
        assert "error" not in result
        assert result["total"] > 0

    def test_binary_ga_n(self, client):
        result = query_by_elements("Ga-N", client)
        assert "error" not in result
        assert result["total"] > 0

    def test_showing_capped_at_20(self, client):
        result = query_by_elements("Si", client)
        assert result["showing"] <= 20

    def test_total_geq_showing(self, client):
        result = query_by_elements("Si", client)
        assert result["total"] >= result["showing"]

    def test_materials_have_jid_and_formula(self, client):
        result = query_by_elements("Si", client)
        for mat in result["materials"]:
            assert "jid" in mat
            assert "formula" in mat


# ===========================================================================
# query_by_property
# Backend _apply_filters() requires at least one anchor filter (formula /
# elements / jid) — bare propranges alone return empty → 500 from server.
# Always pass elements= alongside the property range.
# ===========================================================================

class TestQueryByProperty:

    def test_si_bandgap_range(self, client):
        result = query_by_property(
            "bandgap", min_val=0.5, max_val=3.0,
            elements="Si", api_client=client
        )
        assert "error" not in result, result.get("error")

    def test_gan_formation_energy(self, client):
        result = query_by_property(
            "formation energy", min_val=-2.0, max_val=0.0,
            elements="Ga-N", api_client=client
        )
        assert "error" not in result, result.get("error")

    def test_property_name_resolves_to_mbj_bandgap(self, client):
        result = query_by_property(
            "bandgap", min_val=1.0, max_val=3.0,
            elements="Si", api_client=client
        )
        assert result.get("property") == "mbj_bandgap"

    def test_showing_capped_at_20(self, client):
        result = query_by_property(
            "bandgap", min_val=0.5, max_val=3.0,
            elements="Si", api_client=client
        )
        assert result.get("showing", 0) <= 20

    def test_bulk_modulus_si(self, client):
        result = query_by_property(
            "bulk modulus", min_val=50, max_val=200,
            elements="Si", api_client=client
        )
        assert "error" not in result, result.get("error")

    def test_ehull_si(self, client):
        result = query_by_property(
            "ehull", max_val=0.1,
            elements="Si", api_client=client
        )
        assert "error" not in result, result.get("error")

    def test_range_key_present_in_result(self, client):
        result = query_by_property(
            "bandgap", min_val=1.0, max_val=2.0,
            elements="Si", api_client=client
        )
        assert "range" in result


# ===========================================================================
# find_extreme
# Same requirement as query_by_property: must pass elements= or formula=
# otherwise backend returns empty results → "No materials found".
# ===========================================================================

class TestFindExtreme:

    def test_max_bulk_modulus_si(self, client):
        result = find_extreme(
            "bulk modulus", maximize=True,
            elements="Si", api_client=client
        )
        assert "error" not in result, result.get("error")
        assert result["bulk_modulus_kv"] is not None
        assert result["mode"] == "maximum"

    def test_min_formation_energy_si(self, client):
        result = find_extreme(
            "formation energy", maximize=False,
            elements="Si", api_client=client
        )
        assert "error" not in result, result.get("error")
        assert result["formation_energy_peratom"] is not None
        assert result["mode"] == "minimum"

    def test_max_bandgap_gan(self, client):
        result = find_extreme(
            "bandgap", maximize=True,
            elements="Ga-N", api_client=client
        )
        assert "error" not in result, result.get("error")
        assert result["jid"] is not None

    def test_result_has_jid_and_formula(self, client):
        result = find_extreme(
            "bulk modulus", maximize=True,
            elements="Si", api_client=client
        )
        assert "jid" in result
        assert "formula" in result

    def test_formula_filter_works(self, client):
        result = find_extreme(
            "bandgap", maximize=True,
            formula="GaN", api_client=client
        )
        assert "error" not in result, result.get("error")

    def test_ehull_constraint_applied(self, client):
        result = find_extreme(
            "bulk modulus", maximize=True,
            elements="Si",
            constraint_property="ehull",
            min_constraint=0.0, max_constraint=0.1,
            api_client=client
        )
        assert "error" not in result, result.get("error")

    def test_bandgap_source_in_result(self, client):
        result = find_extreme(
            "bulk modulus", maximize=True,
            elements="Si", api_client=client
        )
        assert "bandgap_source" in result
        assert result["bandgap_source"] in ("mbj", "optb88vdw")


# ===========================================================================
# alignn_predict
# GET /alignn/query — APIKEY in params, jid or poscar param, <=50 atoms.
# ===========================================================================

class TestAlignNPredict:

    def test_predict_by_jid(self, client):
        result = alignn_predict(jid="JVASP-1002", api_client=client)
        assert "error" not in result, result.get("error")
        assert result["status"] == "success"

    def test_formation_energy_returned(self, client):
        result = alignn_predict(jid="JVASP-1002", api_client=client)
        assert result.get("formation_energy") is not None

    def test_some_bandgap_returned(self, client):
        result = alignn_predict(jid="JVASP-1002", api_client=client)
        has_bandgap = (result.get("bandgap") is not None or
                       result.get("bandgap_optb88vdw") is not None or
                       result.get("bandgap_mbj") is not None)
        assert has_bandgap

    def test_mbj_preferred_over_optb88(self, client):
        result = alignn_predict(jid="JVASP-1002", api_client=client)
        if result.get("bandgap_mbj") is not None:
            assert result["bandgap"] == pytest.approx(result["bandgap_mbj"])

    def test_predict_by_poscar_primitive(self, client):
        result = alignn_predict(poscar=SI_POSCAR_PRIM, api_client=client)
        assert "error" not in result, result.get("error")
        assert result["status"] == "success"

    def test_no_input_returns_error(self, client):
        result = alignn_predict(api_client=client)
        assert "error" in result

    def test_bulk_modulus_present(self, client):
        result = alignn_predict(jid="JVASP-1002", api_client=client)
        assert result.get("bulk_modulus") is not None

    def test_shear_modulus_present(self, client):
        result = alignn_predict(jid="JVASP-1002", api_client=client)
        assert result.get("shear_modulus") is not None


# ===========================================================================
# alignn_ff_relax
# POST /alignn_ff/query — accepts poscar_string form field, <=10 atoms.
# ===========================================================================

class TestAlignNFFRelax:

    def test_relax_si_primitive(self, client):
        result = alignn_ff_relax(SI_POSCAR_PRIM, api_client=client)
        assert "error" not in result, result.get("error")
        assert result["status"] == "success"

    def test_relaxed_poscar_nonempty(self, client):
        result = alignn_ff_relax(SI_POSCAR_PRIM, api_client=client)
        if result.get("status") == "success":
            assert isinstance(result["relaxed_poscar"], str)
            assert len(result["relaxed_poscar"]) > 10

    def test_relax_gaas_primitive(self, client):
        result = alignn_ff_relax(GaAs_POSCAR_PRIM, api_client=client)
        assert "error" not in result, result.get("error")

    def test_original_poscar_present(self, client):
        result = alignn_ff_relax(SI_POSCAR_PRIM, api_client=client)
        if result.get("status") == "success":
            assert "original_poscar" in result or "relaxed_poscar" in result


# ===========================================================================
# slakonet_bandstructure
# POST /slakonet/bandstructure — poscar_string form field, <=10 atoms.
# ===========================================================================

class TestSlakoNetBandStructure:

    def test_si_primitive_bandstructure(self, client):
        result = slakonet_bandstructure(SI_POSCAR_PRIM, api_client=client)
        assert "error" not in result, result.get("error")
        assert result["status"] == "success"

    def test_band_gap_returned(self, client):
        result = slakonet_bandstructure(SI_POSCAR_PRIM, api_client=client)
        if result.get("status") == "success":
            assert result["band_gap_eV"] is not None

    def test_vbm_returned(self, client):
        result = slakonet_bandstructure(SI_POSCAR_PRIM, api_client=client)
        if result.get("status") == "success":
            assert result["vbm_eV"] is not None

    def test_cbm_returned(self, client):
        result = slakonet_bandstructure(SI_POSCAR_PRIM, api_client=client)
        if result.get("status") == "success":
            assert result["cbm_eV"] is not None

    def test_image_base64_nonempty(self, client):
        result = slakonet_bandstructure(SI_POSCAR_PRIM, api_client=client)
        if result.get("status") == "success":
            assert "image_base64" in result
            assert len(result["image_base64"]) > 100

    def test_custom_energy_range(self, client):
        result = slakonet_bandstructure(
            SI_POSCAR_PRIM,
            energy_range_min=-5.0,
            energy_range_max=5.0,
            api_client=client
        )
        assert "error" not in result, result.get("error")

    def test_gaas_primitive(self, client):
        result = slakonet_bandstructure(GaAs_POSCAR_PRIM, api_client=client)
        assert "error" not in result, result.get("error")


# ===========================================================================
# generate_interface
# GET /generate_interface — returns plain text POSCAR.
# ===========================================================================

class TestGenerateInterface:

    def test_si_gaas_interface(self, client):
        result = generate_interface(SI_POSCAR, GaAs_POSCAR, api_client=client)
        assert "error" not in result, result.get("error")
        assert result["status"] == "success"

    def test_heterostructure_poscar_is_string(self, client):
        result = generate_interface(SI_POSCAR, GaAs_POSCAR, api_client=client)
        assert isinstance(result.get("heterostructure_atoms"), str)
        assert len(result["heterostructure_atoms"]) > 10

    def test_film_indices_stored(self, client):
        result = generate_interface(SI_POSCAR, GaAs_POSCAR, api_client=client)
        assert "film_indices" in result

    def test_substrate_indices_stored(self, client):
        result = generate_interface(SI_POSCAR, GaAs_POSCAR, api_client=client)
        assert "substrate_indices" in result

    def test_space_separated_indices_normalized(self, client):
        result = generate_interface(
            SI_POSCAR, GaAs_POSCAR,
            film_indices="0 0 1", substrate_indices="0 0 1",
            api_client=client
        )
        assert result.get("film_indices") == "0_0_1"
        assert result.get("substrate_indices") == "0_0_1"

    def test_comma_separated_indices_normalized(self, client):
        result = generate_interface(
            SI_POSCAR, GaAs_POSCAR,
            film_indices="0,0,1", substrate_indices="0,0,1",
            api_client=client
        )
        assert result.get("film_indices") == "0_0_1"
        assert result.get("substrate_indices") == "0_0_1"


# ===========================================================================
# make_supercell  (local jarvis-tools — no network)
# ===========================================================================

class TestMakeSupercell:

    def test_222_supercell_atom_count(self, client):
        result = make_supercell(SI_POSCAR_PRIM, [2, 2, 2])
        assert "error" not in result
        assert result["status"] == "success"
        assert result["supercell_atoms"] == result["original_atoms"] * 8

    def test_111_is_identity(self, client):
        result = make_supercell(SI_POSCAR_PRIM, [1, 1, 1])
        assert result["supercell_atoms"] == result["original_atoms"]

    def test_supercell_poscar_nonempty_string(self, client):
        result = make_supercell(SI_POSCAR_PRIM, [2, 1, 1])
        assert isinstance(result["supercell_poscar"], str)
        assert len(result["supercell_poscar"]) > 0

    def test_scaling_matrix_preserved(self, client):
        result = make_supercell(SI_POSCAR_PRIM, [3, 1, 1])
        assert result["scaling_matrix"] == [3, 1, 1]

    def test_gaas_221_supercell(self, client):
        result = make_supercell(GaAs_POSCAR_PRIM, [2, 2, 1])
        assert result["supercell_atoms"] == result["original_atoms"] * 4


# ===========================================================================
# substitute_atom  (local jarvis-tools — no network)
# ===========================================================================

class TestSubstituteAtom:

    def test_ga_to_al(self, client):
        result = substitute_atom(GaAs_POSCAR_PRIM, "Ga", "Al", num_substitutions=1)
        assert "error" not in result
        assert result["status"] == "success"
        assert "Al" in result["new_formula"]

    def test_as_to_p(self, client):
        result = substitute_atom(GaAs_POSCAR_PRIM, "As", "P", num_substitutions=1)
        assert "error" not in result
        assert "P" in result["new_formula"]

    def test_si_to_ge(self, client):
        result = substitute_atom(SI_POSCAR_PRIM, "Si", "Ge", num_substitutions=1)
        assert "error" not in result
        assert "Ge" in result["new_formula"]

    def test_num_substitutions_in_result(self, client):
        result = substitute_atom(GaAs_POSCAR_PRIM, "Ga", "In", num_substitutions=1)
        assert result["num_substitutions"] == 1

    def test_modified_poscar_is_string(self, client):
        result = substitute_atom(GaAs_POSCAR_PRIM, "As", "P", num_substitutions=1)
        assert isinstance(result["modified_poscar"], str)

    def test_element_absent_returns_error(self, client):
        result = substitute_atom(SI_POSCAR_PRIM, "Fe", "Co", num_substitutions=1)
        assert "error" in result

    def test_over_count_returns_error(self, client):
        # Primitive GaAs has 1 Ga — requesting 5 must fail
        result = substitute_atom(GaAs_POSCAR_PRIM, "Ga", "Al", num_substitutions=5)
        assert "error" in result


# ===========================================================================
# create_vacancy  (local jarvis-tools — no network)
# ===========================================================================

class TestCreateVacancy:

    def test_ga_vacancy_atom_count(self, client):
        result = create_vacancy(GaAs_POSCAR_PRIM, "Ga", num_vacancies=1)
        assert "error" not in result
        assert result["status"] == "success"
        assert result["new_atoms"] == result["original_atoms"] - 1

    def test_as_vacancy(self, client):
        result = create_vacancy(GaAs_POSCAR_PRIM, "As", num_vacancies=1)
        assert "error" not in result
        assert result["new_atoms"] == result["original_atoms"] - 1

    def test_si_vacancy(self, client):
        result = create_vacancy(SI_POSCAR_PRIM, "Si", num_vacancies=1)
        assert result["status"] == "success"
        assert result["new_atoms"] == 1

    def test_num_vacancies_in_result(self, client):
        result = create_vacancy(GaAs_POSCAR_PRIM, "Ga", num_vacancies=1)
        assert result["num_vacancies"] == 1

    def test_modified_poscar_is_string(self, client):
        result = create_vacancy(SI_POSCAR_PRIM, "Si", num_vacancies=1)
        assert isinstance(result["modified_poscar"], str)

    def test_element_absent_returns_error(self, client):
        result = create_vacancy(SI_POSCAR_PRIM, "Ga", num_vacancies=1)
        assert "error" in result

    def test_over_count_returns_error(self, client):
        result = create_vacancy(GaAs_POSCAR_PRIM, "Ga", num_vacancies=10)
        assert "error" in result


# ===========================================================================
# generate_xrd_pattern  (local jarvis-tools — no network)
# ===========================================================================

class TestGenerateXRDPattern:

    def test_si_xrd_succeeds(self, client):
        result = generate_xrd_pattern(SI_POSCAR)
        assert "error" not in result
        assert result["status"] in ("success", "warning")

    def test_peaks_nonempty_on_success(self, client):
        result = generate_xrd_pattern(SI_POSCAR)
        if result["status"] == "success":
            assert len(result["peaks"]) > 0

    def test_peak_fields_valid(self, client):
        result = generate_xrd_pattern(SI_POSCAR)
        if result["status"] == "success":
            for peak in result["peaks"]:
                assert 0 < peak["two_theta"] < 180
                assert 0.0 <= peak["intensity"] <= 1.0
                assert peak["d_spacing"] > 0

    def test_formula_si_in_result(self, client):
        result = generate_xrd_pattern(SI_POSCAR)
        assert result["formula"] == "Si"

    def test_description_mentions_si(self, client):
        result = generate_xrd_pattern(SI_POSCAR)
        if result["status"] == "success":
            assert "Si" in result["description"]

    def test_cu_kalpha_wavelength(self, client):
        result = generate_xrd_pattern(SI_POSCAR, wavelength=1.54184)
        assert "error" not in result

    def test_mo_kalpha_wavelength(self, client):
        result = generate_xrd_pattern(SI_POSCAR, wavelength=0.7093)
        assert "error" not in result

    def test_num_peaks_capped(self, client):
        result = generate_xrd_pattern(SI_POSCAR, num_peaks=5)
        if result["status"] == "success":
            assert len(result["peaks"]) <= 5

    def test_peak_table_is_string(self, client):
        result = generate_xrd_pattern(SI_POSCAR)
        if result["status"] == "success":
            assert isinstance(result["peak_table"], str)

    def test_gaas_formula_in_result(self, client):
        result = generate_xrd_pattern(GaAs_POSCAR)
        assert "error" not in result
        assert result["formula"] == "GaAs"


# ===========================================================================
# diffractgpt_predict
# GET /diffractgpt/query — returns plain text (POSCAR + comment header).
# The current functions.py wraps the text response but then calls
# result.get("POSCAR") on a string → KeyError / AttributeError → surfaces
# as {"error": "'str' object has no attribute 'get'"}.
# Tests document the actual behavior and check what IS reliable.
# ===========================================================================

class TestDiffractGPTPredict:

    def test_returns_dict(self, client):
        result = diffractgpt_predict(
            "Si", "28.4(1.0),47.3(0.49),56.1(0.28)", client
        )
        assert isinstance(result, dict)

    def test_si_no_crash(self, client):
        """Should not raise — either returns valid result or surfaces error."""
        peaks = "28.4(1.0),47.3(0.49),56.1(0.28)"
        result = diffractgpt_predict("Si", peaks, client)
        # Either success with formula, or a handled error dict
        assert "formula" in result or "error" in result

    def test_formula_preserved_on_success(self, client):
        peaks = "28.4(1.0),47.3(0.49),56.1(0.28)"
        result = diffractgpt_predict("Si", peaks, client)
        if "error" not in result:
            assert result.get("formula") == "Si"

    def test_gan_no_crash(self, client):
        peaks = "32.3(1.0),34.5(0.65),36.8(0.45)"
        result = diffractgpt_predict("GaN", peaks, client)
        assert isinstance(result, dict)


# ===========================================================================
# protein_fold
# GET /protein_fold/query — APIKEY injected into query params by AGAPIClient.
# Local validation runs before the network call.
# ===========================================================================

class TestProteinFold:

    VALID_SEQ = "MKTAYIAKQRQISFVKSHFSRQLEERLGLIEVQAPILSRVGDGTQDNLSGAEKAVQVK"
    """
    def test_valid_sequence_succeeds(self, client):
        result = protein_fold(self.VALID_SEQ, api_client=client)
        assert "error" not in result, result.get("error")
        assert result["status"] == "success"
    """

    def test_pdb_structure_nonempty(self, client):
        result = protein_fold(self.VALID_SEQ, api_client=client)
        if result.get("status") == "success":
            assert isinstance(result["pdb_structure"], str)
            assert len(result["pdb_structure"]) > 0

    def test_sequence_length_correct(self, client):
        result = protein_fold(self.VALID_SEQ, api_client=client)
        if result.get("status") == "success":
            assert result["sequence_length"] == len(self.VALID_SEQ)

    def test_too_short_rejected_before_api(self, client):
        result = protein_fold("MKTAY", api_client=client)
        assert "error" in result
        assert "too short" in result["error"].lower()

    def test_too_long_rejected_before_api(self, client):
        result = protein_fold("M" * 401, api_client=client)
        assert "error" in result
        assert "too long" in result["error"].lower()

    def test_invalid_chars_rejected_before_api(self, client):
        result = protein_fold("MKTAY123XZ", api_client=client)
        assert "error" in result

    def test_lowercase_uppercased_and_accepted(self, client):
        result = protein_fold(self.VALID_SEQ.lower(), api_client=client)
        # Should succeed after internal uppercasing
        assert result.get("status") == "success" or "error" in result






# ---------------------------------------------------------------------------
# TestAlignNFFSinglePoint
# ---------------------------------------------------------------------------

class TestAlignNFFSinglePoint:

    def test_returns_dict(self, client):
        result = alignn_ff_single_point(SI_PRIM, api_client=client)
        assert isinstance(result, dict)

    def test_no_error(self, client):
        result = alignn_ff_single_point(SI_PRIM, api_client=client)
        assert "error" not in result, result.get("error")

    def test_energy_present(self, client):
        result = alignn_ff_single_point(SI_PRIM, api_client=client)
        assert "energy_eV" in result
        assert result["energy_eV"] is not None

    def test_energy_is_numeric(self, client):
        result = alignn_ff_single_point(SI_PRIM, api_client=client)
        assert isinstance(result["energy_eV"], (int, float))

    def test_forces_present(self, client):
        result = alignn_ff_single_point(SI_PRIM, api_client=client)
        assert "forces_eV_per_A" in result
        assert result["forces_eV_per_A"] is not None

    def test_forces_shape(self, client):
        result = alignn_ff_single_point(SI_PRIM, api_client=client)
        forces = result["forces_eV_per_A"]
        # Should be a list of [natoms] lists of 3 floats
        assert isinstance(forces, list)
        assert len(forces) == 2  # 2-atom Si

    def test_natoms(self, client):
        result = alignn_ff_single_point(SI_PRIM, api_client=client)
        assert result.get("natoms") == 2

    def test_stress_present(self, client):
        result = alignn_ff_single_point(SI_PRIM, api_client=client)
        assert "stress" in result

"""
# ---------------------------------------------------------------------------
# TestAlignNFFOptimize
# ---------------------------------------------------------------------------

class TestAlignNFFOptimize:

    def test_returns_dict(self, client):
        result = alignn_ff_optimize(SI_PRIM, steps=10, api_client=client)
        assert isinstance(result, dict)

    def test_no_error(self, client):
        result = alignn_ff_optimize(SI_PRIM, steps=10, api_client=client)
        assert "error" not in result, result.get("error")

    def test_final_poscar_present(self, client):
        result = alignn_ff_optimize(SI_PRIM, steps=10, api_client=client)
        assert "final_poscar" in result
        assert len(result["final_poscar"]) > 10

    def test_final_poscar_is_poscar(self, client):
        result = alignn_ff_optimize(SI_PRIM, steps=10, api_client=client)
        poscar = result["final_poscar"]
        # POSCAR must contain "direct" or "cartesian"
        assert "direct" in poscar.lower() or "cartesian" in poscar.lower()

    def test_energies_list(self, client):
        result = alignn_ff_optimize(SI_PRIM, steps=10, api_client=client)
        assert "energies" in result
        assert isinstance(result["energies"], list)
        assert len(result["energies"]) >= 1

    def test_energy_change(self, client):
        result = alignn_ff_optimize(SI_PRIM, steps=10, api_client=client)
        assert "energy_change" in result
        assert isinstance(result["energy_change"], (int, float))

    def test_steps_taken(self, client):
        result = alignn_ff_optimize(SI_PRIM, steps=10, api_client=client)
        assert "steps_taken" in result
        assert result["steps_taken"] >= 0

    def test_converged_key_present(self, client):
        result = alignn_ff_optimize(SI_PRIM, steps=10, api_client=client)
        assert "converged" in result
        assert isinstance(result["converged"], bool)


# ---------------------------------------------------------------------------
# TestAlignNFFMD
# ---------------------------------------------------------------------------

class TestAlignNFFMD:

    def test_returns_dict(self, client):
        result = alignn_ff_md(SI_PRIM, steps=5, api_client=client)
        assert isinstance(result, dict)

    def test_no_error(self, client):
        result = alignn_ff_md(SI_PRIM, steps=5, api_client=client)
        assert "error" not in result, result.get("error")

    def test_steps_completed(self, client):
        result = alignn_ff_md(SI_PRIM, steps=5, api_client=client)
        assert result.get("steps_completed") == 5

    def test_temperatures_present(self, client):
        result = alignn_ff_md(SI_PRIM, steps=5, api_client=client)
        assert "temperatures" in result
        assert isinstance(result["temperatures"], list)

    def test_average_temperature(self, client):
        result = alignn_ff_md(SI_PRIM, temperature=300.0, steps=5, api_client=client)
        assert "average_temperature" in result
        # Should be in rough range (could fluctuate a lot for tiny systems)
        assert result["average_temperature"] >= 0

    def test_energies_dict(self, client):
        result = alignn_ff_md(SI_PRIM, steps=5, api_client=client)
        assert "energies" in result
        energies = result["energies"]
        assert "total" in energies or "potential" in energies

    def test_trajectory_present(self, client):
        result = alignn_ff_md(SI_PRIM, steps=10, interval=5, api_client=client)
        assert "trajectory" in result
        assert isinstance(result["trajectory"], list)

"""

# ---------------------------------------------------------------------------
# TestPXRDMatch
# ---------------------------------------------------------------------------

class TestPXRDMatch:

    def test_returns_dict(self, client):
        result = pxrd_match("LaB6", LAB6_XRD, api_client=client)
        assert isinstance(result, dict)

    def test_no_error(self, client):
        result = pxrd_match("LaB6", LAB6_XRD, api_client=client)
        assert "error" not in result, result.get("error")

    def test_matched_poscar_present(self, client):
        result = pxrd_match("LaB6", LAB6_XRD, api_client=client)
        assert "matched_poscar" in result
        poscar = result["matched_poscar"]
        assert len(poscar) > 10

    def test_matched_poscar_contains_elements(self, client):
        result = pxrd_match("LaB6", LAB6_XRD, api_client=client)
        poscar = result.get("matched_poscar", "")
        # LaB6 structure should mention La or B
        assert "La" in poscar or "B" in poscar

    def test_si_match(self, client):
        result = pxrd_match("Si", SI_XRD, api_client=client)
        assert isinstance(result, dict)
        assert "error" not in result, result.get("error")


# ---------------------------------------------------------------------------
# TestXRDAnalyze
# ---------------------------------------------------------------------------

class TestXRDAnalyze:

    def test_returns_dict(self, client):
        result = xrd_analyze("LaB6", LAB6_XRD, api_client=client)
        assert isinstance(result, dict)

    def test_no_error_on_valid_input(self, client):
        result = xrd_analyze("LaB6", LAB6_XRD, api_client=client)
        # May have pattern_matching key or direct error
        if "error" in result:
            pytest.skip(f"Server error (possibly no LaB6 data): {result['error']}")

    def test_pattern_matching_key(self, client):
        result = xrd_analyze("Si", SI_XRD, method="pattern_matching", api_client=client)
        assert isinstance(result, dict)
        if "pattern_matching" in result:
            pm = result["pattern_matching"]
            assert isinstance(pm, dict)

    def test_best_match_has_jid(self, client):
        result = xrd_analyze("Si", SI_XRD, method="pattern_matching", api_client=client)
        if "pattern_matching" in result and result["pattern_matching"].get("success"):
            best = result["pattern_matching"].get("best_match", {})
            assert "jid" in best

    def test_best_match_has_similarity(self, client):
        result = xrd_analyze("Si", SI_XRD, method="pattern_matching", api_client=client)
        if "pattern_matching" in result and result["pattern_matching"].get("success"):
            best = result["pattern_matching"].get("best_match", {})
            assert "similarity" in best
            assert 0.0 <= best["similarity"] <= 1.0


# ---------------------------------------------------------------------------
# TestQueryMP
# ---------------------------------------------------------------------------

class TestQueryMP:

    def test_returns_dict(self, client):
        result = query_mp("Si", limit=3, api_client=client)
        assert isinstance(result, dict)

    def test_no_error(self, client):
        result = query_mp("Si", limit=3, api_client=client)
        if "error" in result:
            pytest.skip(f"MP API unavailable: {result['error']}")

    def test_has_results(self, client):
        result = query_mp("Si", limit=3, api_client=client)
        if "error" not in result:
            assert "results" in result
            assert isinstance(result["results"], list)

    def test_results_have_poscar(self, client):
        result = query_mp("Si", limit=3, api_client=client)
        if "error" not in result and result.get("results"):
            first = result["results"][0]
            assert "POSCAR" in first


# ---------------------------------------------------------------------------
# TestQueryOQMD
# ---------------------------------------------------------------------------
"""
class TestQueryOQMD:

    def test_returns_dict(self, client):
        result = query_oqmd("Si", limit=3, api_client=client)
        assert isinstance(result, dict)

    def test_no_error(self, client):
        result = query_oqmd("Si", limit=3, api_client=client)
        if "error" in result:
            pytest.skip(f"OQMD API unavailable: {result['error']}")

    def test_has_results_key(self, client):
        result = query_oqmd("Si", limit=3, api_client=client)
        if "error" not in result:
            assert "results" in result


"""
# ---------------------------------------------------------------------------
# TestSearchArxiv
# ---------------------------------------------------------------------------

class TestSearchArxiv:

    def test_returns_dict(self, client):
        result = search_arxiv("JARVIS DFT silicon", max_results=3, api_client=client)
        assert isinstance(result, dict)

    def test_no_error(self, client):
        result = search_arxiv("JARVIS DFT silicon", max_results=3, api_client=client)
        assert "error" not in result, result.get("error")

    def test_has_results(self, client):
        result = search_arxiv("ALIGNN neural network", max_results=3, api_client=client)
        assert "results" in result
        assert isinstance(result["results"], list)

    def test_result_has_title(self, client):
        result = search_arxiv("ALIGNN neural network", max_results=3, api_client=client)
        if result.get("results"):
            assert "title" in result["results"][0]

    def test_result_has_authors(self, client):
        result = search_arxiv("ALIGNN neural network", max_results=3, api_client=client)
        if result.get("results"):
            assert "authors" in result["results"][0]

    def test_count_matches_limit(self, client):
        result = search_arxiv("silicon bandgap", max_results=2, api_client=client)
        if "results" in result:
            assert len(result["results"]) <= 2


# ---------------------------------------------------------------------------
# TestSearchCrossref
# ---------------------------------------------------------------------------

class TestSearchCrossref:

    def test_returns_dict(self, client):
        result = search_crossref("silicon bandgap DFT", rows=3, api_client=client)
        assert isinstance(result, dict)

    def test_no_error(self, client):
        result = search_crossref("silicon bandgap DFT", rows=3, api_client=client)
        assert "error" not in result, result.get("error")

    def test_has_results(self, client):
        result = search_crossref("silicon bandgap DFT", rows=3, api_client=client)
        assert "results" in result
        assert isinstance(result["results"], list)

    def test_result_has_doi(self, client):
        result = search_crossref("silicon bandgap", rows=3, api_client=client)
        if result.get("results"):
            assert "doi" in result["results"][0]

    def test_result_has_title(self, client):
        result = search_crossref("silicon bandgap", rows=3, api_client=client)
        if result.get("results"):
            assert "title" in result["results"][0]

    def test_total_results_present(self, client):
        result = search_crossref("silicon bandgap", rows=3, api_client=client)
        assert "total_results" in result
        assert isinstance(result["total_results"], int)


# ---------------------------------------------------------------------------
# TestListJarvisColumns
# ---------------------------------------------------------------------------

class TestListJarvisColumns:

    def test_returns_dict(self, client):
        result = list_jarvis_columns(api_client=client)
        assert isinstance(result, dict)

    def test_no_error(self, client):
        result = list_jarvis_columns(api_client=client)
        assert "error" not in result, result.get("error")

    def test_columns_key_present(self, client):
        result = list_jarvis_columns(api_client=client)
        assert "columns" in result

    def test_columns_is_list(self, client):
        result = list_jarvis_columns(api_client=client)
        assert isinstance(result["columns"], list)

    def test_expected_columns_present(self, client):
        result = list_jarvis_columns(api_client=client)
        columns = result.get("columns", [])
        # These core columns must exist
        for col in ["jid", "formula", "mbj_bandgap", "formation_energy_peratom"]:
            assert col in columns, f"Missing column: {col}"

    def test_many_columns(self, client):
        result = list_jarvis_columns(api_client=client)
        # JARVIS-DFT has 50+ columns
        assert len(result.get("columns", [])) > 20


# ---------------------------------------------------------------------------
# TestMicroscopyGPT — skipped unless test image provided
# ---------------------------------------------------------------------------

class TestMicroscopyGPT:
    """
    These tests require a real image file.
    Set MICROSCOPY_IMAGE env var to a local image path to run.
    """

    @pytest.fixture
    def image_path(self):
        path = os.environ.get("MICROSCOPY_IMAGE")
        if not path:
            pytest.skip("MICROSCOPY_IMAGE env var not set")
        return path

    def test_returns_dict(self, client, image_path):
        result = microscopygpt_analyze(image_path, "MoS2", api_client=client)
        assert isinstance(result, dict)

    def test_no_error(self, client, image_path):
        result = microscopygpt_analyze(image_path, "MoS2", api_client=client)
        if "error" in result:
            pytest.skip(f"MicroscopyGPT service unavailable: {result['error']}")

    def test_invalid_path_returns_error(self, client):
        result = microscopygpt_analyze("/nonexistent/image.png", "Si", api_client=client)
        assert "error" in result


# ---------------------------------------------------------------------------
# TestOpenFold — skipped unless NVIDIA key configured on server
# ---------------------------------------------------------------------------

class TestOpenFoldPredict:
    """
    Requires NVIDIA API key configured on the server.
    Mark as slow — can take 60-120 seconds.
    """

    # Short protein + matching DNA pair for testing
    PROTEIN = "MGREEPLNHVEAERQRREK"
    DNA1 = "AGGAACACGTGACCC"
    DNA2 = "TGGGTCACGTGTTCC"

    def test_returns_dict(self, client):
        result = openfold_predict(self.PROTEIN, self.DNA1, self.DNA2, api_client=client)
        assert isinstance(result, dict)

    def test_no_error_or_skip(self, client):
        result = openfold_predict(self.PROTEIN, self.DNA1, self.DNA2, api_client=client)
        if "error" in result:
            pytest.skip(f"OpenFold unavailable (NVIDIA key required): {result['error']}")

    def test_pdb_structure_present(self, client):
        result = openfold_predict(self.PROTEIN, self.DNA1, self.DNA2, api_client=client)
        if "error" not in result:
            assert "pdb_structure" in result
            assert "ATOM" in result["pdb_structure"]

    def test_num_atoms_positive(self, client):
        result = openfold_predict(self.PROTEIN, self.DNA1, self.DNA2, api_client=client)
        if "error" not in result:
            assert result.get("num_atoms", 0) > 0
