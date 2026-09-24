import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from src.pass_through import extended_counterfactual, fit_pass_through


def _frame() -> pd.DataFrame:
    path = Path(__file__).resolve().parents[1] / "data" / "processed" / "monthly_series.csv"
    return pd.read_csv(path, parse_dates=["date"])


def test_pass_through_model_fits_on_saved_snapshot():
    model = fit_pass_through(_frame())
    assert model.summary["stage1_observations"] >= 100
    assert np.isfinite(model.summary["nonfuel_all_items_log_change_per_1pct_diesel"])


def test_extended_diesel_shock_increases_projected_all_items_index():
    model = fit_pass_through(_frame())
    base = extended_counterfactual(329.0081819737615, 327.104, 328.481, 0.0, 0.0, model, 317.26466666666664)
    shocked = extended_counterfactual(329.0081819737615, 327.104, 328.481, 0.0, 0.10, model, 317.26466666666664)
    assert shocked["september_cpi_w_all_items"] > base["september_cpi_w_all_items"]
    assert np.isfinite(shocked["cola_raw_pct"])
