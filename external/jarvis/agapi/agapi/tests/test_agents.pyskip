import os
import time
import inspect
import pytest
from agapi.agents import AGAPIAgent


# ============================================================
# Fixture
# ============================================================

@pytest.fixture(scope="session")
def agent():
    api_key = os.environ.get("AGAPI_KEY")
    if not api_key:
        pytest.skip("AGAPI_KEY not set in environment")
    return AGAPIAgent(api_key=api_key)


# ============================================================
# Utility Functions
# ============================================================

def pretty_print(query, response, elapsed):
    test_name = inspect.stack()[1].function
    line = "=" * 120

    print(f"\n{line}")
    print(f"TEST: {test_name}")
    print(f"TIME: {elapsed:.2f} sec")
    print("-" * 120)
    print("QUERY:")
    print(query.strip())
    print("-" * 120)
    print("RESPONSE:")
    print(response)
    print(f"{line}\n")


def run_query(agent, query, **kwargs):
    start = time.time()
    response = agent.query_sync(query, **kwargs)
    elapsed = time.time() - start
    pretty_print(query, response, elapsed)
    return response


def assert_valid_response(resp):
    assert resp is not None
    assert isinstance(resp, str)
    assert len(resp.strip()) > 0


# ============================================================
# Basic Queries
# ============================================================

def test_capital_query(agent):
    query = "Whats the capital of US?"
    resp = run_query(agent, query, render_html=True)
    assert_valid_response(resp)


def test_al2o3_with_tools(agent):
    query = "Find all Al2O3 materials"
    resp = run_query(agent, query, render_html=True)
    assert_valid_response(resp)


def test_al2o3_without_tools(agent):
    query = "Find all Al2O3 materials"
    resp = run_query(agent, query, render_html=True, use_tools=False)
    assert_valid_response(resp)


# ============================================================
# Materials Database Queries
# ============================================================

@pytest.mark.parametrize("query", [
    "Show me all MgB2 polymorphs",
    "Get POSCAR for JVASP-1002",
    "How many materials have Tc_supercon data?",
    "What’s the Tc_Supercon for MgB2 and whats the JARVIS-ID for it?",
    "What’s the Tc_Supercon for NbC in K?",
    "What’s the Tc_Supercon for NbO in K?",
    "What’s the stiffest Si,O material?",
    "Find materials with bulk modulus > 200 GPa",
    "Compare bandgaps across BN, AlN, GaN, InN",
    "What are the formation energies of SiC, AlN, MgO?",
])
def test_material_queries(agent, query):
    resp = run_query(agent, query, render_html=True)
    assert_valid_response(resp)


# ============================================================
# Comparison Queries
# ============================================================

@pytest.mark.parametrize("query", [
    "Compare the bulk moduli and formation energies of TiC, ZrC, HfC",
    "Compare properties of Si, SiC, SiGe",
    "Among materials with bulk modulus > 150 GPa, which has the lowest ehull?",
    "For TiO2, which polymorph is stiffest?",
])
def test_comparison_queries(agent, query):
    resp = run_query(agent, query, render_html=True)
    assert_valid_response(resp)


# ============================================================
# ALIGNN Prediction
# ============================================================

def test_alignn_prediction_jvasp(agent):
    query = "Predict properties of JARVIS-ID JVASP-1002 with ALIGNN"
    resp = run_query(agent, query, render_html=True)
    assert_valid_response(resp)


def test_alignn_prediction_poscar(agent):
    poscar = """System
1.0
3.2631502048902807 0.0 0.0
0.0 3.2631502048902807 0.0
0.0 0.0 3.2631502048902807
Ti Au
1 1
direct
0.5 0.5 0.5
0.0 0.0 0.0
"""
    query = f"Predict properties using ALIGNN for this structure:\n\n{poscar}"
    resp = run_query(agent, query, render_html=True)
    assert_valid_response(resp)


def test_alignn_ff_optimization(agent):
    poscar = """System
1.0
3.2631502048902807 0.0 0.0
0.0 3.2631502048902807 0.0
0.0 0.0 3.2631502048902807
Ti Au
1 1
direct
0.5 0.5 0.5
0.0 0.0 0.0
"""
    query = f"Optimize structure with ALIGNN-FF:\n\n{poscar}"
    resp = run_query(agent, query, render_html=True)
    assert_valid_response(resp)


# ============================================================
# Complex Workflows (Slow Tests)
# ============================================================

@pytest.mark.slow
def test_complex_gan_workflow(agent):
    query = """
    1. Find all GaN materials in the JARVIS-DFT database
    2. Get the POSCAR for the most stable one
    3. Make a 2x1x1 supercell
    4. Substitute one Ga with Al
    5. Generate powder XRD pattern
    6. Optimize structure with ALIGNN-FF
    7. Predict properties with ALIGNN
    """
    resp = run_query(
        agent,
        query,
        render_html=True,
        verbose=True,
        max_context_messages=20,
    )
    assert_valid_response(resp)


@pytest.mark.slow
def test_interface_generation(agent):
    query = """
    Create a GaN/AlN heterostructure interface:
    1. Find GaN (most stable)
    2. Find AlN (most stable)
    3. Generate (001)/(001) interface
    4. Show POSCAR
    """
    resp = run_query(
        agent,
        query,
        render_html=True,
        verbose=True,
        max_context_messages=20,
    )
    assert_valid_response(resp)

