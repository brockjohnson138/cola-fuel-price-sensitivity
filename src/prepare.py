"""Normalize BLS API output and create analysis-ready tables."""

from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

from .acquire import SERIES

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw"
PROCESSED = ROOT / "data" / "processed"


def flatten_series(raw_path: Path | None = None) -> pd.DataFrame:
    raw_path = raw_path or (RAW / "bls_series.json")
    body = json.loads(raw_path.read_text())
    rows: list[dict] = []
    name_by_id = {value: key for key, value in SERIES.items()}
    for series in body["Results"]["series"]:
        series_name = name_by_id.get(series["seriesID"], series["seriesID"])
        for item in series.get("data", []):
            period = item["period"]
            if not period.startswith("M") or period == "M13":
                continue
            if item.get("value") in {None, "", "-"}:
                continue
            rows.append(
                {
                    "series_name": series_name,
                    "series_id": series["seriesID"],
                    "year": int(item["year"]),
                    "month": int(period[1:]),
                    "period": period,
                    "value": float(item["value"]),
                }
            )
    frame = pd.DataFrame(rows).sort_values(["series_name", "year", "month"])
    frame["date"] = pd.to_datetime(
        frame["year"].astype(str) + "-" + frame["month"].astype(str) + "-01"
    )
    return frame.reset_index(drop=True)


def build_tables() -> dict[str, Path]:
    PROCESSED.mkdir(parents=True, exist_ok=True)
    frame = flatten_series()
    monthly_path = PROCESSED / "monthly_series.csv"
    frame.to_csv(monthly_path, index=False)

    pivot = frame.pivot(index="date", columns="series_name", values="value").reset_index()
    q3 = pivot[pivot["date"].dt.month.isin([7, 8, 9])].copy()
    q3["year"] = q3["date"].dt.year
    quarterly = (
        q3.groupby("year", as_index=False)
        .agg(
            q3_cpi_w_all_items=("cpi_w_all_items", "mean"),
            q3_cpi_w_core=("cpi_w_core", "mean"),
            q3_motor_fuel=("cpi_w_motor_fuel", "mean"),
            q3_gasoline=("cpi_w_gasoline", "mean"),
            q3_other_motor_fuels=("cpi_w_other_motor_fuels", "mean"),
            q3_truck_transportation_ppi=("ppi_truck_transportation", "mean"),
            observed_months=("cpi_w_all_items", "count"),
        )
    )
    quarterly_path = PROCESSED / "quarterly_series.csv"
    quarterly.to_csv(quarterly_path, index=False)

    manifest = {
        "source": "BLS Public Data API v2; truck PPI snapshot may use the FRED BLS mirror when the API quota is unavailable",
        "series": SERIES,
        "monthly_rows": int(len(frame)),
        "last_observation_by_series": {
            name: frame.loc[frame["series_name"].eq(name), "date"].max().strftime("%Y-%m-%d")
            for name in SERIES
        },
        "notes": [
            "CPI-W all items and fuel component indexes are not seasonally adjusted.",
            "CPI-W core is all items less food and energy and is used only as a broad downstream price proxy.",
            "Truck transportation PPI is a freight-price proxy, not a direct measure of diesel costs.",
            "Other motor fuels includes automotive diesel and alternative motor fuels.",
            "September 2026 was unavailable at the time of the snapshot and is forecast/scenario-driven.",
        ],
    }
    manifest_path = PROCESSED / "data_manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2))
    return {"monthly": monthly_path, "quarterly": quarterly_path, "manifest": manifest_path}


if __name__ == "__main__":
    print(build_tables())
