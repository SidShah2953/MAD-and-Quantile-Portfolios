#!/usr/bin/env python3
"""
Export the numbers behind the figures as JSON, so the video can draw its charts
natively (frame-driven) instead of holding a static PNG for ten seconds.

Everything here comes from the paper's own loaders in Paper/scripts/, and the
terminal-PV grid is asserted against the numbers printed on the published
heatmap before anything is written.

Usage:  python tools/export_chart_data.py
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

VIDEO_ROOT = Path(__file__).resolve().parents[1]
PROJECT_ROOT = VIDEO_ROOT.parent
OUT = VIDEO_ROOT / "public" / "data"
sys.path.insert(0, str(PROJECT_ROOT))
sys.path.insert(0, str(VIDEO_ROOT / "tools"))

from Paper.scripts.utils.constants import FREQ_ORDER, RISK_ORDER, STRATEGY_ORDER
from Paper.scripts.utils.figure_helpers import load_metric, load_weights

TC = "0 bps Transaction Cost"
RISK = "10.00%"
LABELS = {"S&P BnH": "S&P 500", "95%": "P95"}

# Printed on Paper/LaTeX/figures/heatmap_terminal_pv_zero_cost.png.
EXPECTED_PV = {
    "S&P BnH":    [[469, 469, 469, 469], [469, 469, 469, 469], [469, 469, 469, 469]],
    "Volatility": [[208, 177, 258, 234], [318, 324, 441, 378], [356, 422, 652, 424]],
    "MAD":        [[211, 215, 258, 230], [313, 351, 512, 410], [355, 424, 674, 443]],
    "IQR":        [[284, 242, 328, 215], [371, 339, 657, 390], [424, 432, 756, 465]],
    "95%":        [[241, 208, 253, 217], [329, 378, 458, 475], [374, 461, 711, 421]],
}


def terminal_pv_grid() -> dict[str, list[list[float]]]:
    grid = {}
    for strategy in STRATEGY_ORDER:
        g = []
        for risk in RISK_ORDER:
            row = []
            for freq in FREQ_ORDER:
                try:
                    pv = load_metric(TC, risk, freq, "PV")[strategy].dropna()
                    row.append(round(float(pv.iloc[-1]), 2) if len(pv) else None)
                except (FileNotFoundError, KeyError):
                    row.append(None)
            g.append(row)
        grid[strategy] = g
    return grid


def check_pv(grid) -> list[str]:
    bad = []
    for s, want in EXPECTED_PV.items():
        for i in range(3):
            for j in range(4):
                got = grid[s][i][j]
                if got is None or abs(got - want[i][j]) > 1.0:
                    bad.append(f"{s} {RISK_ORDER[i]} {FREQ_ORDER[j]}: got {got}, published {want[i][j]}")
    return bad


def pv_curves() -> dict:
    """Indexed to 100 at the first observation, weekly, at the 10% risk budget."""
    out = {}
    for freq in FREQ_ORDER:
        df = load_metric(TC, RISK, freq, "PV")
        series = {}
        for strategy in STRATEGY_ORDER:
            if strategy not in df.columns:
                continue
            s = df[strategy].dropna()
            if s.empty:
                continue
            s = (s / float(s.iloc[0])) * 100.0
            s = s.resample("W").last().dropna()
            series[LABELS.get(strategy, strategy)] = [round(float(v), 2) for v in s.values]
        idx = df[STRATEGY_ORDER[0]].dropna().resample("W").last().dropna().index
        out[freq] = {"dates": [d.strftime("%Y-%m") for d in idx], "series": series}
    return out


def weight_paths() -> dict:
    """
    Monthly weight paths on one shared grid, so the four tenures can be tweened
    against each other rather than cross-dissolved as images. Weights are held
    constant between rebalances, so a forward-fill onto the monthly grid is the
    exact representation, not an approximation.
    """
    grid = pd.date_range("1999-01-31", "2025-12-31", freq="ME")
    out: dict = {"dates": [d.strftime("%Y-%m") for d in grid], "tenures": {}}
    cols_ref = None
    for freq in FREQ_ORDER:
        per_strategy = {}
        for strategy in STRATEGY_ORDER:
            if strategy == "S&P BnH":
                continue
            try:
                w = load_weights(TC, RISK, freq, strategy)
            except FileNotFoundError:
                continue
            w = w[w.abs().sum(axis=1) > 1e-9]
            if w.empty:
                continue
            if cols_ref is None:
                cols_ref = list(w.columns)
            w = w.reindex(columns=cols_ref)
            filled = w.reindex(grid.union(w.index)).ffill().reindex(grid)
            per_strategy[LABELS.get(strategy, strategy)] = [
                [None if pd.isna(v) else round(float(v), 1) for v in filled[c].values] for c in cols_ref
            ]
        out["tenures"][freq] = per_strategy

    # Weights only exist from the first rebalance onward, and that date differs
    # by tenure. Trim every tenure to the latest common start so the four share
    # one x-axis and can be interpolated against each other index for index.
    start = 0
    for per_strategy in out["tenures"].values():
        for series in per_strategy.values():
            for row in series:
                first = next((i for i, v in enumerate(row) if v is not None), len(row))
                start = max(start, first)
    out["dates"] = out["dates"][start:]
    for per_strategy in out["tenures"].values():
        for name, series in per_strategy.items():
            per_strategy[name] = [row[start:] for row in series]
    out["columns"] = cols_ref or []
    out["trimmedLeading"] = start
    return out


def dispersion() -> dict:
    """
    The motivation figure's statistic, per calendar half-year: the pooled
    sector-ETF return dispersion with and without the 1.5xIQR outliers.
    Reuses the paper's own compute_semiannual_stats so the numbers are its own.
    """
    from Paper.scripts.figures.generate_motivation_figure import compute_semiannual_stats
    from Paper.scripts.utils.figure_helpers import load_combined_data

    st = compute_semiannual_stats(load_combined_data()).sort_values("halfyear")
    return {
        "periods": [str(v) for v in st["halfyear"]],
        "stdAll": [round(float(v), 6) for v in st["std_all"]],
        "stdTrimmed": [round(float(v), 6) for v in st["std_trimmed"]],
        "nOutliers": [int(v) for v in st["n_outliers"]],
    }


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)

    pv = terminal_pv_grid()
    problems = check_pv(pv)
    if problems:
        print("terminal PV does not match the published heatmap:")
        for p in problems:
            print("  ", p)
        return 1
    print(f"terminal PV matches the published heatmap in all {5 * 12} cells")

    import build_fullsample_mdd_figure as fsm

    mdd = fsm.build_grid()
    bad = fsm.check(mdd)
    if bad:
        print("full-sample MDD diverged:", *bad, sep="\n  ")
        return 1
    print(f"full-sample MDD agrees in all 48 cells; max deviation {fsm.max_deviation(mdd):.3f}pp")

    (OUT / "heatmaps.json").write_text(json.dumps({
        "risks": RISK_ORDER,
        "freqs": FREQ_ORDER,
        "pv": {LABELS.get(k, k): v for k, v in pv.items()},
        "pvOrder": [LABELS.get(s, s) for s in STRATEGY_ORDER],
        "mdd": {LABELS.get(k, k): [[round(float(x), 1) for x in row] for row in g.tolist()]
                for k, g in mdd.items()},
        "mddOrder": [LABELS.get(s, s) for s in fsm.PANELS],
    }))
    (OUT / "pv_curves.json").write_text(json.dumps(pv_curves()))
    (OUT / "dispersion.json").write_text(json.dumps(dispersion()))
    (OUT / "weights.json").write_text(json.dumps(weight_paths()))

    for f in sorted(OUT.glob("*.json")):
        print(f"  {f.name}  {f.stat().st_size / 1024:.0f} KB")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
