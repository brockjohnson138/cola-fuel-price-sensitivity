# Evidence and definitions

The project uses the official Social Security Administration and Bureau of Labor Statistics definitions:

- SSA calculates a COLA from the percentage increase in the average CPI-W for July, August, and September of the current year over the comparison third quarter, rounded to the nearest tenth of one percent.
- For the 2027 COLA, the comparison quarter is Q3 2025 because the last COLA became effective in 2025.
- BLS publishes CPI-W as a monthly, not-seasonally-adjusted index. The project uses `CWUR0000SA0` for all items, `CWUR0000SETB01` for gasoline (all types), and `CWUR0000SETB02` for other motor fuels, which includes automotive diesel and alternative fuels.
- The extended model adds `CWUR0000SA0L1E` (CPI-W all items less food and energy) as a broad nonfuel price diagnostic and `PCU484---484---` (PPI truck transportation, NAICS 484) as a freight-price proxy.
- Fuel-price scenarios use December 2025 CPI-W relative-importance shares published by BLS: gasoline 3.971% and other motor fuels 0.107%.

The pass-through extension uses two lagged Ridge regressions. The first estimates the historical response of truck-transportation PPI to diesel-price changes. The second estimates the response of the all-items CPI-W change remaining after the direct motor-fuel contribution is removed. The resulting response is applied as a counterfactual indirect increment. This is useful for scenario analysis, but it should not be interpreted as a causal estimate of the effect of any particular future diesel-price movement.

The raw-versus-rounded diagnostic is intentional. The project retains the unrounded COLA through the calculation and rounds once to the nearest tenth. A raw result such as 3.446% is 3.4% under that rule; rounding to 3.45% first and then to 3.5% would be double rounding.

As of the project snapshot, September 2026 CPI-W was not available. The outputs therefore separate a transparent September baseline forecast from fuel-price counterfactuals. Rerunning with the October BLS release replaces the forecast with the observed September CPI-W and makes the COLA arithmetic exact.
