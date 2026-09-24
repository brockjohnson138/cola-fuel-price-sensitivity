import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from src.analysis import cola_rounded, cola_raw, fuel_counterfactual, required_september_index


def test_ssa_example_rounds_to_2_8_percent():
    assert np.isclose(cola_raw(317.265, 308.729), 2.764884, atol=1e-6)
    assert cola_rounded(317.265, 308.729) == 2.8


def test_required_september_index_increases_with_target():
    low = required_september_index(317.265, 2.8, 327.104, 328.481)
    high = required_september_index(317.265, 2.9, 327.104, 328.481)
    assert high > low


def test_fuel_shock_grid_is_monotone_in_gasoline_shock():
    low = fuel_counterfactual(317.265, 327.104, 328.481, 330.0, gasoline_shock=0.0)
    high = fuel_counterfactual(317.265, 327.104, 328.481, 330.0, gasoline_shock=0.5)
    assert high["cola_raw_pct"] > low["cola_raw_pct"]


def test_zero_shock_is_finite():
    result = fuel_counterfactual(317.265, 327.104, 328.481, 330.0)
    assert np.isfinite(result["cola_raw_pct"])
