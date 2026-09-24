# Evidence and definitions

The project uses the official Social Security Administration and Bureau of Labor Statistics definitions:

- SSA calculates a COLA from the percentage increase in the average CPI-W for July, August, and September of the current year over the comparison third quarter, rounded to the nearest tenth of one percent.
- For the 2027 COLA, the comparison quarter is Q3 2025 because the last COLA became effective in 2025.
- BLS publishes CPI-W as a monthly, not-seasonally-adjusted index. The project uses `CWUR0000SA0` for all items, `CWUR0000SETB01` for gasoline (all types), and `CWUR0000SETB02` for other motor fuels, which includes automotive diesel and alternative fuels.
- Fuel-price scenarios use December 2025 CPI-W relative-importance shares published by BLS: gasoline 3.971% and other motor fuels 0.107%.

As of the project snapshot, September 2026 CPI-W was not available. The outputs therefore separate a transparent September baseline forecast from fuel-price counterfactuals. Rerunning with the October BLS release replaces the forecast with the observed September CPI-W and makes the COLA arithmetic exact.
