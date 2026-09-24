"""Historical validation for the September CPI-W baseline forecast."""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.dummy import DummyRegressor
from sklearn.linear_model import Ridge
from sklearn.metrics import mean_absolute_error
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler
from sklearn.compose import ColumnTransformer

ROOT = Path(__file__).resolve().parents[1]


def build_features(frame: pd.DataFrame) -> pd.DataFrame:
    pivot = frame.pivot(index="date", columns="series_name", values="value").sort_index()
    result = pivot.copy()
    result["month"] = result.index.month
    result["year"] = result.index.year
    result["lag_1"] = result["cpi_w_all_items"].shift(1)
    result["lag_3"] = result["cpi_w_all_items"].shift(3)
    result["lag_12"] = result["cpi_w_all_items"].shift(12)
    result["gas_change"] = result["cpi_w_gasoline"].pct_change(fill_method=None)
    result["other_motor_fuel_change"] = result["cpi_w_other_motor_fuels"].pct_change(fill_method=None)
    result["all_change"] = result["cpi_w_all_items"].pct_change(fill_method=None)
    return result.reset_index()


def validate_baseline(frame: pd.DataFrame) -> pd.DataFrame:
    """Compare a seasonal-median baseline with a ridge model on historical Sep values."""
    feature = build_features(frame)
    rows = []
    for year in range(2019, 2026):
        train = feature[(feature["year"] < year) & feature["all_change"].notna()].copy()
        test = feature[(feature["year"] == year) & (feature["month"] == 9)].copy()
        if len(test) != 1 or len(train) < 36:
            continue
        # Predict the September index using the prior month and fuel indexes.
        cols = ["lag_1", "lag_3", "lag_12", "cpi_w_gasoline", "cpi_w_other_motor_fuels", "month"]
        train = train.dropna(subset=cols + ["all_change"])
        x_train, y_train = train[cols], train["all_change"]
        x_test, y_test = test[cols], test["cpi_w_all_items"]
        numeric = [c for c in cols if c != "month"]
        pre = ColumnTransformer(
            [("numeric", StandardScaler(), numeric), ("month", OneHotEncoder(handle_unknown="ignore"), ["month"])],
            remainder="drop",
        )
        ridge = make_pipeline(pre, Ridge(alpha=10.0)).fit(x_train, y_train)
        ridge_change = float(ridge.predict(x_test)[0])
        ridge_pred = float(test["lag_1"].iloc[0] * (1.0 + ridge_change))
        prior = feature[feature["year"] < year]
        prior_pivot = prior.pivot(index="year", columns="month", values="cpi_w_all_items")
        seasonal_change = ((prior_pivot[9] / prior_pivot[8]) - 1.0).dropna().median()
        seasonal_pred = float(test["lag_1"].iloc[0] * (1.0 + seasonal_change))
        rows.extend(
            [
                {"test_year": year, "model": "seasonal_median", "actual": float(y_test.iloc[0]), "prediction": seasonal_pred},
                {"test_year": year, "model": "ridge", "actual": float(y_test.iloc[0]), "prediction": ridge_pred},
            ]
        )
    result = pd.DataFrame(rows)
    if result.empty:
        return result
    return (
        result.groupby("model", as_index=False)
        .apply(lambda g: pd.Series({"mae": mean_absolute_error(g["actual"], g["prediction"]), "n": len(g)}), include_groups=False)
        .reset_index(drop=True)
    )
