"""Audit consistency between LaTeX tables and Output metrics.

This script is meant to answer: are the numbers shown in the paper internally
consistent and comparable to the underlying backtest outputs?

It checks:
- Sample date range in Data/combined.csv matches what the paper claims.
- Paper LaTeX tables in Paper/LaTeX/tables match values recomputed from Output.
  * summary_zero_cost.tex vs recomputed best-risk summary at 0% TC
  * tc_summary_10pct_risk.tex vs Transaction Cost.xlsx terminal net values
- Basic unit sanity: percent vs decimals; MDD sign conventions.

Run:
  python Paper/scripts/audit_paper_numbers.py
"""

from __future__ import annotations

if __package__ is None or __package__ == "":
    import sys
    from pathlib import Path as _Path

    sys.path.insert(0, str(_Path(__file__).resolve().parents[2]))

import math
import os
import re
from pathlib import Path

import pandas as pd

from Paper.scripts.utils.constants import Config, FREQ_ORDER, RISK_ORDER, STRATEGY_ORDER, TC_ORDER
from Paper.scripts.utils.latex_parse import parse_simple_tabular_rows
from Paper.scripts.utils.output_io import (
    discover_configs as _discover_configs,
    read_metric as _read_metric,
    read_transaction_cost_book as _read_transaction_cost_book,
)


def _project_root() -> Path:
    return Path(__file__).resolve().parents[2]


def _read_env(project_root: Path) -> dict[str, str]:
    env_path = project_root / ".env"
    out: dict[str, str] = {}
    if env_path.exists():
        for line in env_path.read_text().splitlines():
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            k, v = line.split("=", 1)
            out[k.strip()] = v.strip()
    return out


def discover_configs(output_root: Path) -> set[Config]:
    return set(_discover_configs(output_root))


def read_metric(output_root: Path, cfg: Config, metric_name: str) -> pd.DataFrame:
    return _read_metric(output_root, cfg, metric_name)


def read_transaction_cost_book(output_root: Path, cfg: Config) -> pd.DataFrame:
    return _read_transaction_cost_book(output_root, cfg)


def _years_between(start: pd.Timestamp, end: pd.Timestamp) -> float:
    if pd.isna(start) or pd.isna(end):
        return float("nan")
    return max((end - start).days / 365.25, 1e-9)


def _cagr(pv_start: float, pv_end: float, years: float) -> float:
    if years <= 0 or pv_start <= 0 or pv_end <= 0:
        return float("nan")
    return (pv_end / pv_start) ** (1.0 / years) - 1.0


def summarize_config(output_root: Path, cfg: Config) -> pd.DataFrame:
    pv = read_metric(output_root, cfg, "PV")
    mdd = read_metric(output_root, cfg, "MDD")
    vol = read_metric(output_root, cfg, "Volatility")
    sharpe = read_metric(output_root, cfg, "Sharpe")

    idx = pd.to_datetime(pv.index.astype(str), errors="coerce")
    years = _years_between(idx.min(), idx.max())

    rows = []
    for strat in [s for s in STRATEGY_ORDER if s in pv.columns]:
        pv_s = pv[strat].dropna()
        if len(pv_s) == 0:
            continue
        pv_start = float(pv_s.iloc[0])
        pv_end = float(pv_s.iloc[-1])
        cagr = _cagr(pv_start, pv_end, years)
        rows.append(
            {
                "Strategy": strat,
                "Terminal PV": pv_end,
                "CAGR": cagr,
                "MDD": float(mdd[strat].min()) if strat in mdd.columns else float("nan"),
                "AnnVol": float(vol[strat].replace([math.inf, -math.inf], pd.NA).dropna().mean())
                if strat in vol.columns
                else float("nan"),
                "Sharpe": float(sharpe[strat].replace([math.inf, -math.inf], pd.NA).dropna().mean())
                if strat in sharpe.columns
                else float("nan"),
            }
        )
    return pd.DataFrame(rows).set_index("Strategy")


def _parse_latex_table_rows(tex: str) -> list[list[str]]:
    return parse_simple_tabular_rows(tex)


def _as_float_percent(text: str) -> float:
    # e.g. "6.46\\%" -> 0.0646
    t = text.strip().replace("\\%", "%")
    if t.endswith("%"):
        return float(t[:-1]) / 100.0
    return float(t)


def _as_float(text: str) -> float:
    t = text.strip().replace("\\%", "")
    # for cells like '---'
    if t in ("---", ""):
        return float("nan")
    # If the cell is clearly non-numeric (parsing issue), surface as NaN instead of crashing.
    if re.search(r"[A-Za-z]", t):
        return float("nan")
    return float(t)


def audit_sample_range(project_root: Path) -> list[str]:
    msgs = []
    combined = project_root / "Data" / "combined.csv"
    if not combined.exists():
        return ["FAIL: Data/combined.csv not found"]

    df = pd.read_csv(combined)
    dmin = str(df["Date"].min())
    dmax = str(df["Date"].max())
    msgs.append(f"OK: combined.csv date range = {dmin} to {dmax}")

    env = _read_env(project_root)
    if "START_YEAR" in env and "END_YEAR" in env:
        msgs.append(f"OK: .env START_YEAR={env['START_YEAR']} END_YEAR={env['END_YEAR']}")

    return msgs


def audit_summary_zero_cost(project_root: Path) -> list[str]:
    msgs = []
    output_root = project_root / "Output"
    configs = discover_configs(output_root)

    path = project_root / "Paper" / "LaTeX" / "tables" / "summary_zero_cost.tex"
    if not path.exists():
        return ["SKIP: summary_zero_cost.tex not found"]

    tex = path.read_text()
    rows = _parse_latex_table_rows(tex)
    # header rows include columns; data rows start with freq like 1mo
    data_rows = [r for r in rows if r and r[0] in FREQ_ORDER]
    if not data_rows:
        return ["FAIL: could not parse data rows from summary_zero_cost.tex"]

    # Build expected values: recompute same "best risk by terminal PV" logic
    expected = {}
    tc0 = "0 bps Transaction Cost"
    for freq in FREQ_ORDER:
        for strat in STRATEGY_ORDER:
            best = None
            for risk in RISK_ORDER:
                cfg = Config(tc0, risk, freq)
                if cfg not in configs:
                    continue
                summ = summarize_config(output_root, cfg)
                if strat not in summ.index:
                    continue
                pv_end = float(summ.loc[strat, "Terminal PV"])
                if best is None or pv_end > best["Terminal PV"]:
                    best = {"risk": risk, **summ.loc[strat].to_dict()}
            if best is not None:
                expected[(freq, strat)] = best

    mismatches = 0
    for r in data_rows:
        # Frequency, Strategy, Best Risk, Terminal PV, CAGR, MDD, AnnVol, Sharpe, Turnover
        freq, strat = r[0], r[1].replace("\\&", "&")
        key = (freq, strat)
        if key not in expected:
            msgs.append(f"WARN: row {freq}/{strat} present in LaTeX but missing in Output")
            continue

        exp = expected[key]
        got_risk = r[2]
        got_terminal = _as_float(r[3])
        got_cagr = _as_float_percent(r[4])
        got_mdd = _as_float(r[5])
        got_vol = _as_float(r[6])
        got_sharpe = _as_float(r[7])

        # Expected formatting in LaTeX: terminal PV and MDD/vol are already percent numbers (not decimals)
        exp_terminal = float(exp["Terminal PV"])
        exp_cagr = float(exp["CAGR"])
        exp_mdd = float(exp["MDD"])  # already negative percent in Metrics/MDD.xlsx
        exp_vol = float(exp["AnnVol"])  # percent units
        exp_sharpe = float(exp["Sharpe"])

        # tolerances
        if got_risk != exp["risk"]:
            mismatches += 1
        if not math.isclose(got_terminal, exp_terminal, rel_tol=0, abs_tol=0.02):
            mismatches += 1
        if not math.isclose(got_cagr, exp_cagr, rel_tol=0, abs_tol=5e-4):
            mismatches += 1
        if not math.isclose(got_mdd, exp_mdd, rel_tol=0, abs_tol=0.05):
            mismatches += 1
        if not math.isclose(got_vol, exp_vol, rel_tol=0, abs_tol=0.05):
            mismatches += 1
        if not math.isclose(got_sharpe, exp_sharpe, rel_tol=0, abs_tol=5e-3):
            mismatches += 1

    if mismatches == 0:
        msgs.append("OK: summary_zero_cost.tex matches Output-derived recomputation (within tolerance)")
    else:
        msgs.append(f"FAIL: summary_zero_cost.tex mismatch count = {mismatches}")

    return msgs


def audit_tc_summary_10pct(project_root: Path) -> list[str]:
    msgs = []
    output_root = project_root / "Output"
    configs = discover_configs(output_root)

    path = project_root / "Paper" / "LaTeX" / "tables" / "tc_summary_10pct_risk.tex"
    if not path.exists():
        return ["SKIP: tc_summary_10pct_risk.tex not found"]

    tex = path.read_text()
    rows = _parse_latex_table_rows(tex)
    data_rows = [r for r in rows if r and r[0] in FREQ_ORDER]
    if not data_rows:
        return ["FAIL: could not parse data rows from tc_summary_10pct_risk.tex"]

    # Expected: for each freq/strategy, terminal net PV from Transaction Cost.xlsx at tc=0/1/2
    mismatches = 0
    for r in data_rows:
        freq = r[0]
        strat = r[1].replace("\\&", "&")

        # LaTeX table values are terminal net PVs under cost rates.
        got_pv0 = _as_float(r[2])
        got_pv1 = _as_float(r[3])
        got_pv2 = _as_float(r[4])

        for tc_label, got in [("0 bps Transaction Cost", got_pv0), ("1 bps Transaction Cost", got_pv1), ("2 bps Transaction Cost", got_pv2)]:
            cfg = Config(tc_label, "10.00%", freq)
            if cfg not in configs:
                msgs.append(f"WARN: missing Output config {tc_label}/{cfg.risk_label}/{freq}")
                continue
            book = read_transaction_cost_book(output_root, cfg)
            if (strat, "Net Invested") not in book.columns:
                msgs.append(f"WARN: missing strategy {strat} in Transaction Cost.xlsx for {tc_label}/{freq}")
                continue
            s = book[(strat, "Net Invested")].dropna().astype(float)
            if len(s) == 0:
                continue
            exp = float(s.iloc[-1])
            if not math.isclose(got, exp, rel_tol=0, abs_tol=0.05):
                mismatches += 1

    if mismatches == 0:
        msgs.append("OK: tc_summary_10pct_risk.tex matches Output transaction-cost ledgers (within tolerance)")
    else:
        msgs.append(f"FAIL: tc_summary_10pct_risk.tex mismatch count = {mismatches}")

    return msgs


def audit_comparability_notes() -> list[str]:
    return [
        "NOTE: Metrics/* are computed from daily returns within each holding period; Sharpe columns are annualized-return-per-period divided by annualized risk computed from daily returns in that period.",
        "NOTE: Terminal PV is directly comparable only within the same transaction-cost scenario and same initial value. Cross-frequency comparisons embed different numbers of rebalances and thus different cost incidence.",
    ]


def main() -> None:
    project_root = _project_root()
    print(f"Project root: {project_root}")

    checks = [
        ("Sample range", audit_sample_range),
        ("Summary 0%", audit_summary_zero_cost),
        ("TC summary 10%", audit_tc_summary_10pct),
    ]

    any_fail = False
    for title, fn in checks:
        print(f"\n== {title} ==")
        for msg in fn(project_root):
            print(msg)
            if msg.startswith("FAIL"):
                any_fail = True

    print("\n== Comparability notes ==")
    for msg in audit_comparability_notes():
        print(msg)

    if any_fail:
        raise SystemExit(2)


if __name__ == "__main__":
    main()
