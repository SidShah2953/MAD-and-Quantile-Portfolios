from __future__ import annotations

import math
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

import pandas as pd


@dataclass(frozen=True)
class Config:
    tc_label: str  # e.g. "0 bps Transaction Cost"
    risk_label: str  # e.g. "10.00%"
    freq_label: str  # e.g. "6mo"


STRATEGY_ORDER = ["S&P BnH", "Volatility", "MAD", "IQR", "95%"]
FREQ_ORDER = ["1mo", "3mo", "6mo", "1y"]
RISK_ORDER = ["5.00%", "10.00%", "15.00%"]
TC_ORDER = ["0 bps Transaction Cost", "1 bps Transaction Cost", "2 bps Transaction Cost"]


FREQ_TRADING_DAYS = {
    "1mo": 21,
    "3mo": 63,
    "6mo": 126,
    "1y": 252,
}


def _annualized_return_from_period_returns(period_returns: pd.Series, period_days: int) -> float:
    """Compute geometric annualized return from period returns.

    period_returns are per-holding-period simple returns (decimal, e.g. 0.02).
    """
    s = period_returns.replace([math.inf, -math.inf], pd.NA).dropna().astype(float)
    if len(s) == 0:
        return float("nan")

    gross = float((1.0 + s).prod())
    years = (len(s) * period_days) / 252.0
    if years <= 0 or gross <= 0:
        return float("nan")
    return gross ** (1.0 / years) - 1.0


def _annualized_vol_from_period_returns(period_returns: pd.Series, period_days: int) -> float:
    """Annualize volatility from holding-period returns."""
    s = period_returns.replace([math.inf, -math.inf], pd.NA).dropna().astype(float)
    if len(s) < 2:
        return float("nan")
    return float(s.std(ddof=1) * math.sqrt(252.0 / period_days))


def _annualized_sharpe_from_period_returns(period_returns: pd.Series, period_days: int) -> float:
    ann_ret = _annualized_return_from_period_returns(period_returns, period_days=period_days)
    ann_vol = _annualized_vol_from_period_returns(period_returns, period_days=period_days)
    if pd.isna(ann_ret) or pd.isna(ann_vol) or ann_vol == 0:
        return float("nan")
    return float(ann_ret / ann_vol)




def _parse_period_index(index: pd.Index) -> pd.DatetimeIndex:
    # Most sheets use string dates like '1999-01-04'
    return pd.to_datetime(index.astype(str), errors="coerce")


def _years_between(start: pd.Timestamp, end: pd.Timestamp) -> float:
    if pd.isna(start) or pd.isna(end):
        return float("nan")
    return max((end - start).days / 365.25, 1e-9)


def _cagr(pv_start: float, pv_end: float, years: float) -> float:
    if years <= 0 or pv_start <= 0 or pv_end <= 0:
        return float("nan")
    return (pv_end / pv_start) ** (1.0 / years) - 1.0


def discover_configs(output_root: Path) -> list[Config]:
    configs: list[Config] = []
    for tc_dir in TC_ORDER:
        tc_path = output_root / tc_dir
        if not tc_path.exists():
            continue
        for risk_dir in RISK_ORDER:
            risk_path = tc_path / risk_dir
            if not risk_path.exists():
                continue
            for freq_dir in FREQ_ORDER:
                freq_path = risk_path / freq_dir
                if not freq_path.exists():
                    continue
                configs.append(Config(tc_dir, risk_dir, freq_dir))
    return configs


def read_metric(output_root: Path, cfg: Config, metric_name: str) -> pd.DataFrame:
    path = output_root / cfg.tc_label / cfg.risk_label / cfg.freq_label / "Metrics" / f"{metric_name}.xlsx"
    df = pd.read_excel(path, index_col=0)
    return df


def read_turnover(output_root: Path, cfg: Config) -> pd.DataFrame:
    path = output_root / cfg.tc_label / cfg.risk_label / cfg.freq_label / "Weights" / "Comparison.xlsx"
    df = pd.read_excel(path, index_col=0)
    return df


def read_transaction_cost_book(output_root: Path, cfg: Config) -> pd.DataFrame:
    path = output_root / cfg.tc_label / cfg.risk_label / cfg.freq_label / "Transaction Cost.xlsx"
    # Multi-row header: strategy × {Invested, Transaction Cost, Net Invested}
    df = pd.read_excel(path, header=[0, 1], index_col=0)
    return df


def summarize_config(output_root: Path, cfg: Config) -> pd.DataFrame:
    pv = read_metric(output_root, cfg, "PV")
    mdd = read_metric(output_root, cfg, "MDD")
    vol = read_metric(output_root, cfg, "Volatility")
    # Sharpe.xlsx is a per-period diagnostic that depends on period construction.
    # For the paper summary table we instead report a mechanically reproducible annual Sharpe:
    # Sharpe = CAGR / AnnVol (rf=0), using the displayed CAGR and AnnVol.
    turnover = read_turnover(output_root, cfg)

    idx = _parse_period_index(pv.index)
    start = idx.min()
    end = idx.max()
    years = _years_between(start, end)

    out_rows = []
    for strat in [c for c in STRATEGY_ORDER if c in pv.columns]:
        pv_start = float(pv[strat].dropna().iloc[0])
        pv_end = float(pv[strat].dropna().iloc[-1])
        cagr = _cagr(pv_start, pv_end, years)

        # MDD is stored as negative percent values; report magnitude (positive percent).
        mdd_raw = float(mdd[strat].min()) if strat in mdd.columns else float("nan")
        mdd_mag = (-mdd_raw) if (not pd.isna(mdd_raw) and mdd_raw <= 0) else mdd_raw

        # These are already annualized in percent units (volatility) and unitless for Sharpe.
        vol_mean = float(vol[strat].replace([math.inf, -math.inf], pd.NA).dropna().mean()) if strat in vol.columns else float("nan")
        sharpe_annual = float("nan")
        if not pd.isna(cagr) and not pd.isna(vol_mean) and vol_mean != 0:
            # vol_mean is in percent points (e.g., 15.92 for 15.92%), so convert to decimal.
            sharpe_annual = float(cagr / (vol_mean / 100.0))
        turnover_mean = _reduce_metric_series(turnover[strat], "mean_excluding_ends") if strat in turnover.columns else float("nan")

        out_rows.append(
            {
                "Strategy": strat,
                "Terminal PV": pv_end,
                "CAGR": cagr,
                "MDD": mdd_mag,
                "AnnVol": vol_mean,
                "Sharpe": sharpe_annual,
                "Turnover": turnover_mean,
            }
        )

    return pd.DataFrame(out_rows).set_index("Strategy")


def terminal_net_pv(output_root: Path, cfg: Config) -> pd.Series:
    tc = read_transaction_cost_book(output_root, cfg)
    out = {}
    for strat in tc.columns.levels[0]:
        if (strat, "Net Invested") not in tc.columns:
            continue
        s = tc[(strat, "Net Invested")].dropna()
        if len(s) == 0:
            continue
        out[strat] = float(s.iloc[-1])
    return pd.Series(out)


def latex_escape_text(text: str) -> str:
    # Minimal LaTeX escaping for strings that may contain special chars.
    # We intentionally keep this small and focused for labels in tables.
    return (
        text.replace("\\", "\\textbackslash{}")
        .replace("&", "\\&")
        .replace("%", "\\%")
        .replace("_", "\\_")
        .replace("#", "\\#")
        .replace("$", "\\$")
        .replace("{", "\\{")
        .replace("}", "\\}")
    )


def _format_percent(x: float, decimals: int = 2) -> str:
    if pd.isna(x):
        return "---"
    return f"{100*x:.{decimals}f}\\%"


def _format_number(x: float, decimals: int = 2) -> str:
    if pd.isna(x):
        return "---"
    return f"{x:.{decimals}f}"


def write_table(path: Path, caption: str, label: str, tabular_latex: str) -> None:
    content = "\n".join(
        [
            "\\begin{table}[H]",
            "  \\centering",
            f"  \\caption{{{caption}}}",
            f"  \\label{{{label}}}",
            tabular_latex,
            "\\end{table}",
            "",
        ]
    )
    path.write_text(content)


def read_weights(output_root: Path, cfg: Config, strategy: str) -> pd.DataFrame:
    path = output_root / cfg.tc_label / cfg.risk_label / cfg.freq_label / "Weights" / f"{strategy}.xlsx"
    df = pd.read_excel(path, index_col=0)
    # Drop any all-NaN rows (e.g., placeholder first period rows).
    return df.dropna(how="all")


def write_weights_longtable(path: Path, weights: pd.DataFrame, caption: str, label: str) -> None:
    """Write a LaTeX longtable of portfolio weights.

    Designed for multi-page tables (e.g., monthly frequency).
    """
    df = weights.copy()
    df.index = df.index.astype(str)

    df = df.astype(float)
    # The pipeline exports weights to Excel already in percent units (0–100).
    # For robustness, detect fractional weights (0–1) and convert to percent.
    max_abs = float(df.abs().max().max()) if df.size else 0.0
    if max_abs <= 1.5:
        df = df * 100.0

    # Format weights as percents for readability.
    df = df.round(2)

    col_names = [latex_escape_text(str(c)) for c in df.columns]
    n_cols = 1 + len(col_names)  # period + assets
    col_spec = "l" + ("r" * len(col_names))

    header = "Period & " + " & ".join(col_names) + " \\\\"  # noqa: W605
    rows = []
    for period, row in df.iterrows():
        values = [f"{v:.2f}" if not pd.isna(v) else "---" for v in row.values]
        rows.append(latex_escape_text(str(period)) + " & " + " & ".join(values) + " \\\\ ")

    content = "\n".join(
        [
            "\\begin{center}",
            "\\scriptsize",
            "\\setlength{\\tabcolsep}{3pt}",
            f"\\begin{{longtable}}{{{col_spec}}}",
            f"\\caption{{{caption}}}\\label{{{label}}}\\\\",
            "\\toprule",
            header,
            "\\midrule",
            "\\endfirsthead",
            f"\\multicolumn{{{n_cols}}}{{c}}{{\\tablename\\ \\thetable\\ -- continued from previous page}}\\\\",
            "\\toprule",
            header,
            "\\midrule",
            "\\endhead",
            f"\\midrule \\multicolumn{{{n_cols}}}{{r}}{{Continued on next page}}\\\\",
            "\\endfoot",
            "\\bottomrule",
            "\\endlastfoot",
            *rows,
            "\\end{longtable}",
            "\\end{center}",
            "",
        ]
    )
    path.write_text(content)


def _reduce_metric_series(values: pd.Series, reducer: str) -> float:
    s = values.replace([math.inf, -math.inf], pd.NA).dropna()
    if len(s) == 0:
        return float("nan")
    if reducer == "mean_excluding_ends":
        if len(s) <= 2:
            return float("nan")
        s = s.iloc[1:-1]
        return float(s.mean()) if len(s) else float("nan")
        turnover_mean = _reduce_metric_series(turnover[strat], "mean_excluding_ends") if strat in turnover.columns else float("nan")
    if reducer == "terminal":
        return float(s.iloc[-1])
    if reducer == "mean":
        return float(s.mean())
    if reducer == "min":
        return float(s.min())
    if reducer == "max":
        return float(s.max())
    raise ValueError(f"Unknown reducer: {reducer}")


def build_tables(project_root: Path) -> None:
    output_root = project_root / "Output"
    latex_root = project_root / "Paper" / "LaTeX"
    tables_root = latex_root / "tables"
    tables_root.mkdir(parents=True, exist_ok=True)

    configs = discover_configs(output_root)
    if not configs:
        raise RuntimeError(f"No configs found under {output_root}")

    # --- Main Table (Table 1): full grid at 0% cost (all risks × all frequencies × all strategies) ---
    # Requirement: sort by risk first, then frequency, then strategy name.
    # Benchmark (S&P BnH) is shown once as the first row and not repeated.
    tc0 = "0 bps Transaction Cost"
    rows: list[dict] = []

    for risk in RISK_ORDER:
        for freq in FREQ_ORDER:
            cfg = Config(tc0, risk, freq)
            if cfg not in configs:
                continue
            summ = summarize_config(output_root, cfg)
            for strat in STRATEGY_ORDER:
                if strat == "S&P BnH":
                    continue
                if strat not in summ.index:
                    continue
                rows.append(
                    {
                        "Risk": risk,
                        "Frequency": freq,
                        "Strategy": strat,
                        **summ.loc[strat].to_dict(),
                    }
                )

    grid_df = pd.DataFrame(rows)

    # Pick a single benchmark row for S&P BnH (independent of risk).
    bnh_row = None
    bnh_best_years = -1.0
    for cfg in configs:
        if cfg.tc_label != tc0:
            continue
        try:
            pv = read_metric(output_root, cfg, "PV")
        except Exception:
            continue
        if "S&P BnH" not in pv.columns:
            continue
        idx = _parse_period_index(pv.index)
        years = _years_between(idx.min(), idx.max())
        if years > bnh_best_years:
            bnh_best_years = years
            bnh_row = summarize_config(output_root, cfg).loc["S&P BnH"].to_dict()

    # Sorting keys
    risk_rank = {r: i for i, r in enumerate(RISK_ORDER)}
    freq_rank = {f: i for i, f in enumerate(FREQ_ORDER)}

    if not grid_df.empty:
        grid_df["_risk_sort"] = grid_df["Risk"].map(risk_rank).fillna(999)
        grid_df["_freq_sort"] = grid_df["Frequency"].map(freq_rank).fillna(999)
        grid_df["_strat_sort"] = grid_df["Strategy"].astype(str)
        grid_df = grid_df.sort_values(["_risk_sort", "_freq_sort", "_strat_sort"]).drop(
            columns=["_risk_sort", "_freq_sort", "_strat_sort"]
        )

    # Prepend benchmark row once
    if bnh_row is not None:
        bnh_df = pd.DataFrame(
            [
                {
                    "Risk": "All",
                    "Frequency": "All",
                    "Strategy": "S&P BnH",
                    **bnh_row,
                }
            ]
        )
        grid_df = pd.concat([bnh_df, grid_df], ignore_index=True)

    # Format for LaTeX
    grid_df["Risk"] = grid_df["Risk"].map(latex_escape_text)
    grid_df["Frequency"] = grid_df["Frequency"].map(latex_escape_text)
    grid_df["Strategy"] = grid_df["Strategy"].map(latex_escape_text)
    grid_df["CAGR"] = grid_df["CAGR"].map(lambda x: _format_percent(x, 2))
    grid_df["Terminal PV"] = grid_df["Terminal PV"].map(lambda x: _format_number(x, 2))
    grid_df["MDD"] = grid_df["MDD"].map(lambda x: _format_number(x, 2))
    grid_df["AnnVol"] = grid_df["AnnVol"].map(lambda x: _format_number(x, 2))
    grid_df["Sharpe"] = grid_df["Sharpe"].map(lambda x: _format_number(x, 3))
    grid_df["Turnover"] = grid_df["Turnover"].map(lambda x: _format_number(x, 3))

    grid_df = grid_df[["Risk", "Frequency", "Strategy", "Terminal PV", "CAGR", "MDD", "AnnVol", "Sharpe", "Turnover"]]

    tab = grid_df.to_latex(index=False, escape=False, longtable=False)

    # Add midrules between risk groups (benchmark row will naturally separate from first risk group).
    tab_lines = tab.split('\n')
    result_lines = []
    prev_risk = None
    for line in tab_lines:
        if '&' in line and '\\\\' in line:
            # Extract risk value from the line (1st column)
            parts = line.split('&')
            if len(parts) >= 1:
                current_risk = parts[0].strip()
                if prev_risk is not None and current_risk != prev_risk:
                    result_lines.append('\\midrule')
                prev_risk = current_risk
        result_lines.append(line)
    tab = '\n'.join(result_lines)

    write_table(
        tables_root / "summary_zero_cost.tex",
        "Performance summary at 0 bps transaction costs across all risk budgets and rebalancing frequencies. Rows are sorted by risk, then frequency, then strategy. S\&P BnH is shown once as a benchmark. MDD values are reported as positive magnitudes (larger values indicate larger drawdowns). Sharpe is computed as CAGR/AnnVol (with AnnVol converted from percent to decimal and $r_f=0$). Turnover is the mean rebalance-to-rebalance sum of absolute \emph{non-cash} weight changes (cash sleeve excluded), matching the transaction-cost model.",
        "tab:summary-zero-cost",
        tab,
    )

    # --- Main TC Table: fixed risk=10% across frequencies, report net PV under 0/1/2 costs ---
    fixed_risk = "10.00%"
    tc_rows = []
    for freq in FREQ_ORDER:
        net0 = terminal_net_pv(output_root, Config("0 bps Transaction Cost", fixed_risk, freq))
        net1 = terminal_net_pv(output_root, Config("1 bps Transaction Cost", fixed_risk, freq))
        net2 = terminal_net_pv(output_root, Config("2 bps Transaction Cost", fixed_risk, freq))
        for strat in STRATEGY_ORDER:
            if strat not in net0.index:
                continue
            pv0 = float(net0[strat])
            pv1 = float(net1.get(strat, float("nan")))
            pv2 = float(net2.get(strat, float("nan")))
            drag2 = (pv2 / pv0 - 1.0) if (pv0 > 0 and not pd.isna(pv2)) else float("nan")
            tc_rows.append(
                {
                    "Frequency": freq,
                    "Strategy": latex_escape_text(strat),
                    "Net PV (0 bps)": _format_number(pv0, 2),
                    "Net PV (1 bps)": _format_number(pv1, 2),
                    "Net PV (2 bps)": _format_number(pv2, 2),
                    "Drag at 2 bps": _format_percent(drag2, 2),
                }
            )

    tc_df = pd.DataFrame(tc_rows)
    # No LaTeX escaping needed here (no % signs now).
    
    # Sort by frequency
    tc_df['_freq_sort'] = tc_df['Frequency'].map({f: i for i, f in enumerate(FREQ_ORDER)})
    tc_df = tc_df.sort_values('_freq_sort').drop(columns=['_freq_sort'])
    
    tc_tab = tc_df.to_latex(index=False, escape=False)
    
    # Add midrules between frequency groups
    tc_tab_lines = tc_tab.split('\n')
    tc_result_lines = []
    tc_prev_freq = None
    for line in tc_tab_lines:
        if '&' in line and '\\\\' in line:
            # Extract frequency from the line
            parts = line.split('&')
            if len(parts) >= 1:
                current_freq = parts[0].strip()
                if tc_prev_freq is not None and current_freq != tc_prev_freq:
                    tc_result_lines.append('\\midrule')
                tc_prev_freq = current_freq
        tc_result_lines.append(line)
    tc_tab = '\n'.join(tc_result_lines)
    write_table(
        tables_root / "tc_summary_10pct_risk.tex",
        "Net terminal portfolio value under proportional transaction costs at 10\\% risk budget. Costs are charged per trade on \emph{non-cash} assets (cash sleeve excluded). Net PV values are computed from the pipeline-generated backtest outputs (\\texttt{Output/.../Transaction Cost.xlsx}). Drag at 2 bps shows the percentage change in terminal value relative to 0 bps costs.",
        "tab:tc-summary",
        tc_tab,
    )

    # Appendix tables were intentionally removed from the paper build to keep the paper streamlined.

    # --- Turnover comparison table: all risks × all frequencies (0 bps) ---
    tc_focus = "0 bps Transaction Cost"
    turnover_rows = []
    for risk_focus in RISK_ORDER:
        for freq in FREQ_ORDER:
            cfg = Config(tc_focus, risk_focus, freq)
            if cfg not in configs:
                continue
            turnover = read_turnover(output_root, cfg)
            row = {"Risk": latex_escape_text(risk_focus), "Frequency": freq}
            for strat in STRATEGY_ORDER:
                if strat in turnover.columns:
                    row[latex_escape_text(strat)] = _reduce_metric_series(turnover[strat], "mean_excluding_ends")
            turnover_rows.append(row)

    if turnover_rows:
        tdf = pd.DataFrame(turnover_rows)
        tdf["_risk_sort"] = tdf["Risk"].map({r: i for i, r in enumerate([latex_escape_text(r) for r in RISK_ORDER])})
        tdf["_freq_sort"] = tdf["Frequency"].map({f: i for i, f in enumerate(FREQ_ORDER)})
        tdf = tdf.sort_values(["_risk_sort", "_freq_sort"]).drop(columns=["_risk_sort", "_freq_sort"])

        for strat in [latex_escape_text(s) for s in STRATEGY_ORDER]:
            if strat in tdf.columns:
                tdf[strat] = tdf[strat].map(lambda x: _format_number(x, 3))

        tab = tdf.to_latex(index=False, escape=False)

        # Add midrules between risk groups for readability.
        tab_lines = tab.split("\n")
        out_lines = []
        prev_risk = None
        for line in tab_lines:
            if "&" in line and "\\\\" in line:
                parts = line.split("&")
                current_risk = parts[0].strip() if parts else None
                # Only treat data rows (risk values like '10.00\\%') as group keys.
                is_data_row = (current_risk is not None) and ("\\%" in current_risk)
                if is_data_row:
                    if prev_risk is not None and current_risk != prev_risk:
                        out_lines.append("\\midrule")
                    prev_risk = current_risk
            out_lines.append(line)
        tab = "\n".join(out_lines)

        write_table(
            tables_root / "turnover_by_risk_zero_cost.tex",
            "Mean rebalance-to-rebalance sum of absolute \emph{non-cash} weight changes (turnover proxy; cash sleeve excluded) at 0 bps transaction costs, reported across risk budgets and rebalancing frequencies.",
            "tab:turnover-by-risk-zero-cost",
            tab,
        )

    print(f"Wrote tables to: {tables_root}")

    # Appendix weight longtables were intentionally removed from the paper build to keep outputs streamlined.


def main() -> None:
    project_root = Path(__file__).resolve().parents[3]
    build_tables(project_root)


if __name__ == "__main__":
    main()
