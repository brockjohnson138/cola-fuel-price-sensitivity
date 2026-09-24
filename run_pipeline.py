"""Run acquisition, preparation, validation, COLA arithmetic, and fuel scenarios."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))

from src.acquire import main as acquire
from src.analysis import analyze
from src.modeling import validate_baseline
from src.prepare import build_tables


def main(refresh: bool = False) -> dict:
    acquire(refresh=refresh)
    paths = build_tables()
    frame = pd.read_csv(paths["monthly"], parse_dates=["date"])
    summary, thresholds, grid = analyze(frame)
    metrics = validate_baseline(frame)
    out = ROOT / "outputs"
    out.mkdir(exist_ok=True)
    (out / "scenario_summary.json").write_text(json.dumps(summary, indent=2))
    thresholds.to_csv(out / "cola_thresholds.csv", index=False)
    grid.to_csv(out / "fuel_shock_grid.csv", index=False)
    metrics.to_csv(out / "forecast_validation_metrics.csv", index=False)
    print(json.dumps({"summary": summary, "validation_metrics": metrics.to_dict("records")}, indent=2))
    return summary


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--refresh", action="store_true", help="Refresh the BLS snapshot before running.")
    args = parser.parse_args()
    main(refresh=args.refresh)
