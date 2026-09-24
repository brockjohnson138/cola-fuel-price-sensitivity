"""Create compact, reproducible figures for the project README."""

from __future__ import annotations

import json
from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
OUTPUTS = ROOT / "outputs"
FIGURES = ROOT / "docs" / "figures"
FIGURES.mkdir(parents=True, exist_ok=True)


def _style() -> None:
    plt.rcParams.update(
        {
            "figure.facecolor": "white",
            "axes.facecolor": "#f7f9fc",
            "axes.edgecolor": "#cbd5e1",
            "axes.labelcolor": "#243447",
            "axes.titleweight": "bold",
            "font.size": 10,
            "text.color": "#243447",
            "xtick.color": "#475569",
            "ytick.color": "#475569",
        }
    )


def _save(fig: plt.Figure, name: str) -> None:
    fig.tight_layout()
    fig.savefig(FIGURES / name, dpi=180, bbox_inches="tight")
    plt.close(fig)


def make_threshold_figure() -> None:
    summary = json.loads((OUTPUTS / "scenario_summary.json").read_text())
    baseline = summary["baseline_projection"]["cola_raw_pct"]
    rounded = summary["baseline_projection"]["cola_rounded_pct"]
    threshold = summary["raw_rounding_diagnostic"]["next_tenth_raw_threshold_pct"]
    fig, ax = plt.subplots(figsize=(8.5, 4.6))
    labels = ["Baseline raw", "Baseline rounded", "Next tenth threshold"]
    values = [baseline, rounded, threshold]
    colors = ["#2563eb", "#0f766e", "#f59e0b"]
    bars = ax.bar(labels, values, color=colors, width=0.62)
    ax.set_ylabel("COLA (%)")
    ax.set_title("Provisional COLA baseline and next-tenth threshold")
    ax.set_ylim(3.35, 3.52)
    ax.grid(axis="y", alpha=0.25)
    for bar, value in zip(bars, values):
        ax.text(bar.get_x() + bar.get_width() / 2, value + 0.006, f"{value:.3f}%", ha="center", weight="bold")
    fig.text(0.01, 0.01, "Snapshot: September 24, 2026; September CPI-W not yet released.", fontsize=8, color="#64748b")
    _save(fig, "cola_thresholds.png")


def make_surface_figure() -> None:
    grid = pd.read_csv(OUTPUTS / "extended_fuel_shock_grid.csv")
    surface = grid.pivot(index="diesel_shock_pct", columns="gasoline_shock_pct", values="cola_rounded_pct")
    # Keep the README visual focused on the near-threshold range. The full
    # machine-readable grid remains available in outputs/.
    surface = surface.loc[surface.index <= 50, surface.columns <= 50]
    fig, ax = plt.subplots(figsize=(8.5, 5.4))
    image = ax.imshow(
        surface.values,
        origin="lower",
        aspect="auto",
        extent=[surface.columns.min(), surface.columns.max(), surface.index.min(), surface.index.max()],
        cmap="YlGnBu",
    )
    ax.set_xlabel("Gasoline shock (%)")
    ax.set_ylabel("Diesel shock (%)")
    ax.set_title("Rounded COLA under combined fuel scenarios (0–50% shocks)")
    colorbar = fig.colorbar(image, ax=ax)
    colorbar.set_label("Rounded COLA (%)")
    fig.text(0.01, 0.01, "Diesel-to-freight pass-through is exploratory; values are counterfactual scenarios.", fontsize=8, color="#64748b")
    _save(fig, "fuel_shock_surface.png")


def make_validation_figure() -> None:
    metrics = pd.read_csv(OUTPUTS / "forecast_validation_metrics.csv")
    fig, ax = plt.subplots(figsize=(7.5, 4.4))
    colors = ["#0f766e" if model == "seasonal_median" else "#64748b" for model in metrics["model"]]
    bars = ax.bar(metrics["model"].str.replace("_", " ").str.title(), metrics["mae"], color=colors)
    ax.set_ylabel("Mean absolute error")
    ax.set_title("September forecast validation")
    ax.grid(axis="y", alpha=0.25)
    for bar, value in zip(bars, metrics["mae"]):
        ax.text(bar.get_x() + bar.get_width() / 2, value + 0.04, f"{value:.3f}", ha="center", weight="bold")
    n = int(metrics["n"].iloc[0]) if "n" in metrics else None
    if n:
        fig.text(0.01, 0.01, f"Held-out observations: {n}; lower is better.", fontsize=8, color="#64748b")
    _save(fig, "forecast_validation.png")


def main() -> None:
    _style()
    make_threshold_figure()
    make_surface_figure()
    make_validation_figure()


if __name__ == "__main__":
    main()
