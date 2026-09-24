"""COLA arithmetic and direct/indirect fuel-price counterfactuals."""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

from .pass_through import (
    extended_counterfactual,
    fit_pass_through,
)

ROOT = Path(__file__).resolve().parents[1]
PROCESSED = ROOT / "data" / "processed"

# December 2025 CPI-W relative importance published by BLS.
# These are shares of the CPI-W basket, expressed as proportions.
WEIGHTS = {
    "gasoline": 0.03971,  # gasoline, all types: 3.971%
    "other_motor_fuels": 0.00107,  # other motor fuels: 0.107%; includes diesel
}


def round_half_up(value: float, decimals: int = 1) -> float:
    factor = 10**decimals
    return float(np.floor(value * factor + 0.5) / factor)


def cola_raw(q3_current: float, q3_base: float) -> float:
    return 100.0 * (q3_current - q3_base) / q3_base


def cola_rounded(q3_current: float, q3_base: float) -> float:
    return round_half_up(cola_raw(q3_current, q3_base), 1)


def required_september_index(q3_base: float, target_rounded: float, july: float, august: float) -> float:
    """Smallest September all-items index that rounds to the requested COLA."""
    # Values at x.05 round up to x.1 under SSA's nearest-tenth convention.
    raw_floor = target_rounded - 0.05
    target_q3 = q3_base * (1.0 + raw_floor / 100.0)
    return 3.0 * target_q3 - july - august


def september_baseline(frame: pd.DataFrame, series_name: str) -> float:
    """Forecast September by the historical median September-over-August change."""
    series = frame[frame["series_name"].eq(series_name)].copy()
    pivot = series.pivot(index="year", columns="month", values="value")
    changes = ((pivot[9] / pivot[8]) - 1.0).dropna()
    # Use completed pre-2026 years so the current incomplete quarter is not recycled.
    changes = changes[changes.index < 2026]
    return float(pivot.loc[2026, 8] * (1.0 + changes.median()))


def fuel_counterfactual(
    base_q3: float,
    july: float,
    august: float,
    baseline_september: float,
    gasoline_shock: float = 0.0,
    other_motor_fuel_shock: float = 0.0,
) -> dict:
    """Apply a transparent ceteris-paribus fuel shock to September's all-items index."""
    incremental = baseline_september * (
        WEIGHTS["gasoline"] * gasoline_shock
        + WEIGHTS["other_motor_fuels"] * other_motor_fuel_shock
    )
    september = baseline_september + incremental
    q3 = float(np.mean([july, august, september]))
    return {
        "gasoline_shock_pct": gasoline_shock * 100.0,
        "other_motor_fuel_shock_pct": other_motor_fuel_shock * 100.0,
        "september_cpi_w_all_items": september,
        "q3_cpi_w_average": q3,
        "cola_raw_pct": cola_raw(q3, base_q3),
        "cola_rounded_pct": cola_rounded(q3, base_q3),
    }


def _solve_diesel_threshold(
    q3_base: float,
    july: float,
    august: float,
    baseline_september: float,
    required_september: float,
    model,
) -> float:
    """Find the smallest nonnegative diesel shock reaching a COLA threshold."""
    if required_september <= baseline_september:
        return 0.0

    def projected_level(shock: float) -> float:
        return extended_counterfactual(
            baseline_september,
            july,
            august,
            gasoline_shock=0.0,
            diesel_shock=shock,
            model=model,
            base_q3=q3_base,
        )["september_cpi_w_all_items"]

    lower, upper = 0.0, 0.01
    while projected_level(upper) < required_september and upper < 64.0:
        upper *= 2.0
    if projected_level(upper) < required_september:
        return float("nan")
    for _ in range(60):
        midpoint = (lower + upper) / 2.0
        if projected_level(midpoint) >= required_september:
            upper = midpoint
        else:
            lower = midpoint
    return upper


def analyze(frame: pd.DataFrame) -> tuple[dict, pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    pivot = frame.pivot(index="date", columns="series_name", values="value").reset_index()
    q3 = pivot[pivot["date"].dt.month.isin([7, 8, 9])].copy()
    q3["year"] = q3["date"].dt.year
    # Official base for the 2027 COLA is Q3 2025 because the last COLA became effective in 2025.
    q3_2025 = q3[q3["year"].eq(2025)]["cpi_w_all_items"].mean()
    current = pivot[pivot["date"].dt.year.eq(2026)].copy()
    current = current.set_index(current["date"].dt.month)
    july = float(current.loc[7, "cpi_w_all_items"])
    august = float(current.loc[8, "cpi_w_all_items"])
    baseline_sep = september_baseline(frame, "cpi_w_all_items")
    baseline = fuel_counterfactual(q3_2025, july, august, baseline_sep)
    pass_through = fit_pass_through(frame)
    extended_baseline = extended_counterfactual(
        baseline_sep,
        july,
        august,
        gasoline_shock=0.0,
        diesel_shock=0.0,
        model=pass_through,
        base_q3=q3_2025,
    )

    # Determine how much a one-tenth increase over the baseline projected COLA would require.
    target = baseline["cola_rounded_pct"] + 0.1
    needed_sep = required_september_index(q3_2025, target, july, august)
    gap = max(0.0, needed_sep - baseline_sep)
    gasoline_shock = gap / (baseline_sep * WEIGHTS["gasoline"]) if gap else 0.0
    diesel_shock = gap / (baseline_sep * WEIGHTS["other_motor_fuels"]) if gap else 0.0
    gas_price = float(current.loc[8, "avg_gasoline_regular"])
    diesel_price = float(current.loc[8, "avg_diesel"])
    thresholds = []
    for target_cola in np.arange(0.0, 8.1, 0.1):
        needed = required_september_index(q3_2025, float(target_cola), july, august)
        gap_i = max(0.0, needed - baseline_sep)
        gas = gap_i / (baseline_sep * WEIGHTS["gasoline"]) if gap_i else 0.0
        diesel = gap_i / (baseline_sep * WEIGHTS["other_motor_fuels"]) if gap_i else 0.0
        thresholds.append(
            {
                "target_cola_pct": round(float(target_cola), 1),
                "required_september_cpi_w": needed,
                "additional_index_gap": gap_i,
                "gasoline_only_shock_pct": gas * 100.0,
                "gasoline_regular_price_if_only_gas": gas_price * (1.0 + gas),
                "other_motor_fuel_only_shock_pct": diesel * 100.0,
                "diesel_price_if_only_other_motor_fuel": diesel_price * (1.0 + diesel),
            }
        )
    threshold_df = pd.DataFrame(thresholds)

    extended_thresholds = []
    for target_cola in np.arange(0.0, 8.1, 0.1):
        target_value = float(target_cola)
        needed = required_september_index(q3_2025, target_value, july, august)
        diesel = _solve_diesel_threshold(
            q3_2025,
            july,
            august,
            baseline_sep,
            needed,
            pass_through,
        )
        scenario = extended_counterfactual(
            baseline_sep,
            july,
            august,
            gasoline_shock=0.0,
            diesel_shock=0.0 if np.isnan(diesel) else diesel,
            model=pass_through,
            base_q3=q3_2025,
        )
        extended_thresholds.append(
            {
                "target_cola_pct": round(target_value, 1),
                "required_september_cpi_w": needed,
                "diesel_only_shock_pct": diesel * 100.0 if not np.isnan(diesel) else np.nan,
                "diesel_price_if_only_diesel": diesel_price * (1.0 + diesel) if not np.isnan(diesel) else np.nan,
                "direct_index_increment_at_threshold": scenario["direct_index_increment"],
                "indirect_index_increment_at_threshold": scenario["indirect_index_increment"],
            }
        )
    extended_threshold_df = pd.DataFrame(extended_thresholds)

    grid = []
    for gas in np.arange(0.0, 3.01, 0.05):
        for diesel in np.arange(0.0, 3.01, 0.05):
            grid.append(fuel_counterfactual(q3_2025, july, august, baseline_sep, gas, diesel))
    grid_df = pd.DataFrame(grid)
    extended_grid = []
    for gas in np.arange(0.0, 3.01, 0.05):
        for diesel in np.arange(0.0, 3.01, 0.05):
            extended_grid.append(
                extended_counterfactual(
                    baseline_sep,
                    july,
                    august,
                    gasoline_shock=float(gas),
                    diesel_shock=float(diesel),
                    model=pass_through,
                    base_q3=q3_2025,
                )
            )
    extended_grid_df = pd.DataFrame(extended_grid)
    extended_target_diesel = _solve_diesel_threshold(
        q3_2025,
        july,
        august,
        baseline_sep,
        needed_sep,
        pass_through,
    )
    extended_target_scenario = extended_counterfactual(
        baseline_sep,
        july,
        august,
        gasoline_shock=0.0,
        diesel_shock=extended_target_diesel,
        model=pass_through,
        base_q3=q3_2025,
    )
    summary = {
        "as_of": "2026-09-24",
        "status": "September 2026 CPI-W was not yet available; projected and counterfactual results are scenario analysis.",
        "q3_2025_base_cpi_w": q3_2025,
        "july_2026_cpi_w": july,
        "august_2026_cpi_w": august,
        "baseline_september_cpi_w_forecast": baseline_sep,
        "baseline_projection": baseline,
        "raw_rounding_diagnostic": {
            "raw_cola_pct": baseline["cola_raw_pct"],
            "rounded_cola_pct": baseline["cola_rounded_pct"],
            "next_tenth_raw_threshold_pct": target - 0.05,
            "warning": "Round the unrounded COLA once to the nearest tenth; do not round to two decimals first.",
        },
        "next_tenth_target_cola_pct": target,
        "required_september_cpi_w_for_next_tenth": needed_sep,
        "additional_september_index_gap": gap,
        "gasoline_only_shock_pct": gasoline_shock * 100.0,
        "approx_gasoline_regular_price_per_gallon": gas_price * (1.0 + gasoline_shock),
        "other_motor_fuel_only_shock_pct": diesel_shock * 100.0,
        "approx_diesel_price_per_gallon": diesel_price * (1.0 + diesel_shock),
        "weights": WEIGHTS,
        "pass_through_model": pass_through.summary,
        "extended_baseline_projection": extended_baseline,
        "extended_next_tenth_projection": {
            "diesel_only_shock_pct": extended_target_diesel * 100.0,
            "diesel_price_if_only_diesel": diesel_price * (1.0 + extended_target_diesel),
            **extended_target_scenario,
        },
        "interpretation": [
            "Fuel shocks are ceteris-paribus counterfactuals using BLS CPI-W relative-importance weights.",
            "The extended channel estimates diesel-to-trucking-to-nonfuel pass-through from historical monthly relationships; it is not a structural causal estimate.",
            "The calculation does not claim that fuel prices alone determine the COLA.",
            "The September CPI-W release will replace the forecast and make the official COLA arithmetic exact.",
        ],
    }
    return summary, threshold_df, grid_df, extended_threshold_df, extended_grid_df
