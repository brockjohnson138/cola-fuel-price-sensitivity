"""Estimate a transparent fuel-to-freight-to-consumer price channel.

The model is deliberately framed as an exploratory pass-through estimate. It
uses two historical regressions rather than claiming a structural causal
estimate:

1. diesel-price changes -> truck-transportation PPI changes; and
2. truck-transportation PPI changes -> the all-items CPI-W change remaining
   after removing the direct motor-fuel contribution.

The resulting response is used for counterfactual sensitivity scenarios. It
does not assert that every observed historical relationship is causal.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import numpy as np
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.linear_model import Ridge
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler


GASOLINE_WEIGHT = 0.03971
OTHER_MOTOR_FUEL_WEIGHT = 0.00107
MOTOR_FUEL_WEIGHT = GASOLINE_WEIGHT + OTHER_MOTOR_FUEL_WEIGHT


@dataclass
class PassThroughModel:
    stage1: Any
    stage2: Any
    core_stage2: Any
    stage1_features: tuple[str, ...]
    stage2_features: tuple[str, ...]
    core_features: tuple[str, ...]
    summary: dict[str, float | int | str]


def build_features(frame: pd.DataFrame) -> pd.DataFrame:
    """Create monthly log-change features for the two pass-through stages."""
    pivot = frame.pivot(index="date", columns="series_name", values="value").sort_index()
    required = {
        "cpi_w_all_items",
        "cpi_w_core",
        "cpi_w_motor_fuel",
        "avg_diesel",
        "ppi_truck_transportation",
    }
    missing = sorted(required - set(pivot.columns))
    if missing:
        raise ValueError(f"Pass-through series missing from the prepared data: {missing}")

    result = pivot.copy()
    result["month"] = result.index.month
    result["diesel_log_change"] = np.log(result["avg_diesel"]).diff()
    result["truck_log_change"] = np.log(result["ppi_truck_transportation"]).diff()
    result["all_log_change"] = np.log(result["cpi_w_all_items"]).diff()
    if "cpi_w_core" in result:
        result["core_log_change"] = np.log(result["cpi_w_core"]).diff()
    result["motor_fuel_log_change"] = np.log(result["cpi_w_motor_fuel"]).diff()
    # Approximate the all-items change that remains after removing the direct
    # motor-fuel contribution. This retains indirect effects in the residual.
    result["nonfuel_all_items_log_change"] = result["all_log_change"] - (
        MOTOR_FUEL_WEIGHT * result["motor_fuel_log_change"]
    )
    for lag in range(4):
        result[f"diesel_lag_{lag}"] = result["diesel_log_change"].shift(lag)
        result[f"truck_lag_{lag}"] = result["truck_log_change"].shift(lag)
    result["nonfuel_lag_1"] = result["nonfuel_all_items_log_change"].shift(1)
    return result.reset_index()


def _fit_ridge(train: pd.DataFrame, target: str, features: list[str]) -> Any:
    numeric = [column for column in features if column != "month"]
    transformer = ColumnTransformer(
        [
            ("numeric", StandardScaler(), numeric),
            ("month", OneHotEncoder(handle_unknown="ignore"), ["month"]),
        ],
        remainder="drop",
    )
    model = make_pipeline(transformer, Ridge(alpha=1.0))
    model.fit(train[features], train[target])
    return model


def _impulse(model: Any, features: tuple[str, ...], shock_column: str, shock: float) -> float:
    """Return the model's change from a zero-change September baseline."""
    row = {column: (9 if column == "month" else 0.0) for column in features}
    baseline = pd.DataFrame([row])
    shocked = baseline.copy()
    shocked.loc[0, shock_column] = shock
    return float(model.predict(shocked)[0] - model.predict(baseline)[0])


def fit_pass_through(frame: pd.DataFrame) -> PassThroughModel:
    """Fit the two-stage historical pass-through model."""
    features = build_features(frame)
    stage1_features = ("diesel_lag_0", "diesel_lag_1", "diesel_lag_2", "diesel_lag_3", "truck_lag_1", "month")
    stage2_features = ("truck_lag_0", "truck_lag_1", "truck_lag_2", "truck_lag_3", "nonfuel_lag_1", "month")
    stage1_train = features.dropna(subset=list(stage1_features) + ["truck_log_change"])
    stage2_train = features.dropna(subset=list(stage2_features) + ["nonfuel_all_items_log_change"])
    if len(stage1_train) < 36 or len(stage2_train) < 36:
        raise ValueError("Not enough complete monthly observations to fit the pass-through model")

    stage1 = _fit_ridge(stage1_train, "truck_log_change", list(stage1_features))
    stage2 = _fit_ridge(stage2_train, "nonfuel_all_items_log_change", list(stage2_features))
    core_features = stage2_features
    core_train = features.dropna(subset=list(core_features) + ["core_log_change"])
    core_stage2 = _fit_ridge(core_train, "core_log_change", list(core_features))
    one_pct = float(np.log1p(0.01))
    truck_response = _impulse(stage1, stage1_features, "diesel_lag_0", one_pct)
    indirect_response = _impulse(stage2, stage2_features, "truck_lag_0", truck_response)
    core_response = _impulse(core_stage2, core_features, "truck_lag_0", truck_response)
    summary: dict[str, float | int | str] = {
        "method": "two-stage ridge with monthly seasonality and distributed lags",
        "stage1_observations": int(len(stage1_train)),
        "stage2_observations": int(len(stage2_train)),
        "core_stage2_observations": int(len(core_train)),
        "stage1_in_sample_r2": float(stage1.score(stage1_train[list(stage1_features)], stage1_train["truck_log_change"])),
        "stage2_in_sample_r2": float(stage2.score(stage2_train[list(stage2_features)], stage2_train["nonfuel_all_items_log_change"])),
        "core_stage2_in_sample_r2": float(core_stage2.score(core_train[list(core_features)], core_train["core_log_change"])),
        "sample_start": features["date"].min().strftime("%Y-%m-%d"),
        "sample_end": features["date"].max().strftime("%Y-%m-%d"),
        "truck_ppi_log_change_per_1pct_diesel": truck_response,
        "nonfuel_all_items_log_change_per_1pct_diesel": indirect_response,
        "truck_ppi_percent_response_per_1pct_diesel": truck_response * 100.0,
        "indirect_all_items_percent_response_per_1pct_diesel": indirect_response * 100.0,
        "core_percent_response_per_1pct_diesel": core_response * 100.0,
    }
    return PassThroughModel(stage1, stage2, core_stage2, stage1_features, stage2_features, core_features, summary)


def indirect_nonfuel_change(model: PassThroughModel, diesel_shock: float) -> float:
    """Estimate the indirect all-items-equivalent log change from a diesel shock."""
    if diesel_shock <= -1:
        raise ValueError("diesel_shock must be greater than -100 percent")
    diesel_log_change = float(np.log1p(diesel_shock))
    truck_change = _impulse(model.stage1, model.stage1_features, "diesel_lag_0", diesel_log_change)
    return _impulse(model.stage2, model.stage2_features, "truck_lag_0", truck_change)


def extended_counterfactual(
    baseline_september: float,
    july: float,
    august: float,
    gasoline_shock: float,
    diesel_shock: float,
    model: PassThroughModel,
    base_q3: float,
) -> dict[str, float]:
    """Apply direct fuel and estimated indirect freight pass-through effects."""
    direct_increment = baseline_september * (
        GASOLINE_WEIGHT * gasoline_shock + OTHER_MOTOR_FUEL_WEIGHT * diesel_shock
    )
    indirect_log_change = indirect_nonfuel_change(model, diesel_shock)
    indirect_increment = baseline_september * float(np.expm1(indirect_log_change))
    september = baseline_september + direct_increment + indirect_increment
    q3_average = float(np.mean([july, august, september]))
    raw_cola = 100.0 * (q3_average - base_q3) / base_q3
    rounded_cola = float(np.floor(raw_cola * 10.0 + 0.5) / 10.0)
    return {
        "gasoline_shock_pct": gasoline_shock * 100.0,
        "diesel_shock_pct": diesel_shock * 100.0,
        "direct_index_increment": direct_increment,
        "indirect_index_increment": indirect_increment,
        "indirect_log_change": indirect_log_change,
        "september_cpi_w_all_items": september,
        "q3_cpi_w_average": q3_average,
        "cola_raw_pct": raw_cola,
        "cola_rounded_pct": rounded_cola,
    }
