# COLA Fuel-Price Sensitivity

This project estimates how gasoline and diesel-related price movements could affect the Social Security Administration's next Cost-of-Living Adjustment (COLA). It is designed for the period before the September 2026 CPI-W release and can be rerun as soon as BLS publishes that month.

The analysis follows SSA's official rule: compare the average CPI-W for July, August, and September with the comparison third quarter, then round the percentage increase to the nearest tenth of one percent. For the 2027 COLA, the comparison quarter is Q3 2025.

The pipeline combines:

- official BLS CPI-W all-items, core, motor-fuel, gasoline, other-motor-fuel, gasoline-price, diesel-price, and truck-transportation PPI series;
- a transparent September baseline forecast using the historical median September-over-August change;
- a Ridge model benchmarked against that seasonal baseline on historical September observations;
- a fuel-weight counterfactual model that estimates the gasoline or other-motor-fuel shock required to cross each COLA threshold; and
- a two-stage, lagged Ridge pass-through model that estimates diesel -> truck transportation -> nonfuel consumer-price effects; and
- direct and extended 3,721-cell gasoline/diesel shock grids for sensitivity analysis.

The direct model holds other prices fixed. The extended model estimates a historical pass-through channel from diesel prices to truck-transportation PPI and then to the all-items CPI-W change remaining after the direct motor-fuel contribution is removed. It is a transparent sensitivity model, not a structural causal estimate; freight contracts, competition, inventory, fuel efficiency, and timing can all change the actual pass-through. BLS defines “other motor fuels” as including automotive diesel and alternative motor fuels, so the direct diesel result is a proxy for that CPI-W component rather than a diesel-only CPI index. September 2026 is unavailable in the current snapshot, so current outputs are provisional and should be refreshed after the October BLS release.

## Run

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python run_pipeline.py
pytest -q
```

Use `python run_pipeline.py --refresh` to request the latest BLS API snapshot. The default run uses the saved snapshot so the results remain reproducible.

## Outputs

- `outputs/scenario_summary.json` — current baseline, next-tenth COLA target, and fuel-only threshold estimates;
- `outputs/cola_thresholds.csv` — required September CPI-W and gasoline/diesel proxy shocks for each rounded COLA target;
- `outputs/fuel_shock_grid.csv` — combined gasoline and other-motor-fuel counterfactuals;
- `outputs/extended_cola_thresholds.csv` — thresholds after adding estimated diesel-to-freight-to-consumer pass-through;
- `outputs/extended_fuel_shock_grid.csv` — combined direct-plus-indirect counterfactuals;
- `outputs/forecast_validation_metrics.csv` — historical comparison of the seasonal baseline and Ridge model; and
- `data/processed/data_manifest.json` — series IDs, last observations, and data limitations.

See [`docs/EVIDENCE.md`](docs/EVIDENCE.md) for definitions, source series, and limitations and [`docs/PORTFOLIO.md`](docs/PORTFOLIO.md) for the portfolio description.

## Sources

- [SSA COLA methodology](https://www.ssa.gov/cola/)
- [SSA latest COLA calculation example](https://www.ssa.gov/OACT/COLA/latestCOLA.html)
- [BLS CPI-W series documentation](https://www.bls.gov/cpi/factsheets/cpi-series-ids.htm)
- [BLS motor-fuel methodology](https://www.bls.gov/cpi/factsheets/motor-fuel.htm)
- [BLS PPI databases and industry series](https://www.bls.gov/ppi/databases/)
- [Truck transportation PPI mirror](https://fred.stlouisfed.org/series/PCU484484)
- [BLS CPI release schedule](https://www.bls.gov/schedule/2026/)
