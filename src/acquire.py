"""Acquire official BLS CPI-W, fuel-price, and freight-price series."""

from __future__ import annotations

import argparse
import json
import os
from datetime import datetime, timezone
from pathlib import Path

import requests

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw"
BLS_API = "https://api.bls.gov/publicAPI/v2/timeseries/data/"

SERIES = {
    "cpi_w_all_items": "CWUR0000SA0",
    # Broad consumer-price measure used to estimate downstream pass-through.
    "cpi_w_core": "CWUR0000SA0L1E",
    "cpi_w_motor_fuel": "CWUR0000SETB",
    "cpi_w_gasoline": "CWUR0000SETB01",
    # BLS defines this component as other motor fuels; it includes automotive diesel.
    "cpi_w_other_motor_fuels": "CWUR0000SETB02",
    "avg_gasoline_regular": "APU000074714",
    "avg_gasoline_all_types": "APU00007471A",
    "avg_diesel": "APU000074717",
    # BLS PPI industry series: Truck transportation (NAICS 484).
    "ppi_truck_transportation": "PCU484---484---",
}


def fetch_series(start_year: int = 2017, end_year: int = 2026) -> dict:
    """Fetch all required series through the BLS public API.

    The public API limits an unregistered request to ten years, so the
    project uses a ten-year window that includes the current 2026 snapshot.
    """
    verify_ssl = os.getenv("BLS_VERIFY_SSL", "1").lower() not in {"0", "false", "no"}
    response = requests.post(
        BLS_API,
        json={
            "seriesid": list(SERIES.values()),
            "startyear": str(start_year),
            "endyear": str(end_year),
        },
        timeout=60,
        verify=verify_ssl,
    )
    response.raise_for_status()
    body = response.json()
    if body.get("status") != "REQUEST_SUCCEEDED":
        raise RuntimeError(f"BLS API failure: {body.get('message')}")
    return {
        "status": "REQUEST_SUCCEEDED",
        "message": [],
        "Results": body["Results"],
        "retrieved_at_utc": datetime.now(timezone.utc).isoformat(),
        "series_catalog": SERIES,
    }


def main(refresh: bool = False) -> Path:
    RAW.mkdir(parents=True, exist_ok=True)
    path = RAW / "bls_series.json"
    if path.exists() and not refresh:
        return path
    body = fetch_series()
    path.write_text(json.dumps(body, indent=2))
    return path


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--refresh", action="store_true")
    args = parser.parse_args()
    print(main(refresh=args.refresh))
