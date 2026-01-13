from __future__ import annotations

import math
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable
from typing import Callable

import pandas as pd


@dataclass(frozen=True)
class Config:
    tc_label: str  # e.g. "0% Transaction Cost"
    risk_label: str  # e.g. "10.00%"
    freq_label: str  # e.g. "6mo"


STRATEGY_ORDER = ["S&P BnH", "Volatility", "MAD", "IQR", "95%"]
FREQ_ORDER = ["1mo", "3mo", "6mo", "1y"]
RISK_ORDER = ["5.00%", "10.00%", "15.00%", "20.00%"]
TC_ORDER = ["0% Transaction Cost", "1% Transaction Cost", "2% Transaction Cost"]


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


def _moving_block_bootstrap_indices(n: int, block_len: int, rng) -> list[int]:
    if n <= 0:
        return []
    block_len = max(1, min(int(block_len), n))
    starts = list(range(0, n - block_len + 1))
    out: list[int] = []
    while len(out) < n:
        s = rng.choice(starts)
        out.extend(list(range(s, s + block_len)))
    return out[:n]


def _bootstrap_ci(
    x: pd.Series,
    y: pd.Series,
    statistic: Callable[[pd.Series], float],
    n_boot: int,
    block_len: int,
    seed: int,
) -> tuple[float, float, float]:
    """Bootstrap CI for statistic(x) - statistic(y) with moving blocks."""
    xs = x.reset_index(drop=True)
    ys = y.reset_index(drop=True)
    n = min(len(xs), len(ys))
    xs = xs.iloc[:n]
    ys = ys.iloc[:n]
    if n == 0:
        return float("nan"), float("nan"), float("nan")

    import numpy as np

    rng = np.random.default_rng(seed)
    diffs = []
    for _ in range(int(n_boot)):
        idx = _moving_block_bootstrap_indices(n, block_len=block_len, rng=rng)
        diffs.append(statistic(xs.iloc[idx]) - statistic(ys.iloc[idx]))

    diffs = np.asarray(diffs, dtype=float)
    point = statistic(xs) - statistic(ys)
    lo, hi = np.nanpercentile(diffs, [2.5, 97.5])
    return float(point), float(lo), float(hi)


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
    sharpe = read_metric(output_root, cfg, "Sharpe")
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

        # MDD is stored as negative percent values; report the worst drawdown magnitude as a positive percent.
        mdd_worst = float(mdd[strat].min()) if strat in mdd.columns else float("nan")

        # These are already annualized in percent units (volatility) and unitless for Sharpe.
        vol_mean = float(vol[strat].replace([math.inf, -math.inf], pd.NA).dropna().mean()) if strat in vol.columns else float("nan")
        sharpe_mean = float(sharpe[strat].replace([math.inf, -math.inf], pd.NA).dropna().mean()) if strat in sharpe.columns else float("nan")
        turnover_mean = float(turnover[strat].replace([math.inf, -math.inf], pd.NA).dropna().mean()) if strat in turnover.columns else float("nan")

        out_rows.append(
            {
                "Strategy": strat,
                "Terminal PV": pv_end,
                "CAGR": cagr,
                "MDD": mdd_worst,
                "AnnVol": vol_mean,
                "Sharpe": sharpe_mean,
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


def _reduce_metric_series(values: pd.Series, reducer: str) -> float:
    s = values.replace([math.inf, -math.inf], pd.NA).dropna()
    if len(s) == 0:
        return float("nan")
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

    # --- Main Table: best risk per frequency (0% cost) ---
    tc0 = "0% Transaction Cost"
    best_rows = []
    for freq in FREQ_ORDER:
        # choose risk that maximizes terminal PV for each strategy independently
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
                    best = {
                        "Frequency": freq,
                        "Strategy": strat,
                        "Best Risk": risk,
                        **summ.loc[strat].to_dict(),
                    }
            if best is not None:
                best_rows.append(best)

    best_df = pd.DataFrame(best_rows)

    # Format for LaTeX
    best_df["Strategy"] = best_df["Strategy"].map(latex_escape_text)
    best_df["Best Risk"] = best_df["Best Risk"].map(latex_escape_text)
    best_df["CAGR"] = best_df["CAGR"].map(lambda x: _format_percent(x, 2))
    best_df["Terminal PV"] = best_df["Terminal PV"].map(lambda x: _format_number(x, 2))
    best_df["MDD"] = best_df["MDD"].map(lambda x: _format_number(x, 2))
    best_df["AnnVol"] = best_df["AnnVol"].map(lambda x: _format_number(x, 2))
    best_df["Sharpe"] = best_df["Sharpe"].map(lambda x: _format_number(x, 3))
    best_df["Turnover"] = best_df["Turnover"].map(lambda x: _format_number(x, 3))

    best_df = best_df[["Frequency", "Strategy", "Best Risk", "Terminal PV", "CAGR", "MDD", "AnnVol", "Sharpe", "Turnover"]]
    
    # Sort by Best Risk then Frequency
    best_df['_risk_sort'] = best_df['Best Risk'].map({latex_escape_text(r): i for i, r in enumerate(RISK_ORDER)})
    best_df['_freq_sort'] = best_df['Frequency'].map({f: i for i, f in enumerate(FREQ_ORDER)})
    best_df = best_df.sort_values(['_risk_sort', '_freq_sort']).drop(columns=['_risk_sort', '_freq_sort'])

    tab = best_df.to_latex(index=False, escape=False, longtable=False)
    
    # Add midrules between risk groups only
    tab_lines = tab.split('\n')
    result_lines = []
    prev_risk = None
    for line in tab_lines:
        if '&' in line and '\\\\' in line:
            # Extract risk value from the line (3rd column)
            parts = line.split('&')
            if len(parts) >= 3:
                current_risk = parts[2].strip()
                if prev_risk is not None and current_risk != prev_risk:
                    result_lines.append('\\midrule')
                prev_risk = current_risk
        result_lines.append(line)
    tab = '\n'.join(result_lines)
    write_table(
        tables_root / "summary_zero_cost.tex",
        "Performance summary at 0\\% transaction costs. For each strategy and rebalancing frequency, results are shown at the risk budget that maximizes terminal portfolio value. MDD values are negative; turnover is one-way turnover per rebalance.",
        "tab:summary-zero-cost",
        tab,
    )

    # --- Main TC Table: fixed risk=10% across frequencies, report net PV under 0/1/2 costs ---
    fixed_risk = "10.00%"
    tc_rows = []
    for freq in FREQ_ORDER:
        net0 = terminal_net_pv(output_root, Config("0% Transaction Cost", fixed_risk, freq))
        net1 = terminal_net_pv(output_root, Config("1% Transaction Cost", fixed_risk, freq))
        net2 = terminal_net_pv(output_root, Config("2% Transaction Cost", fixed_risk, freq))
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
                    "Net PV (0%)": _format_number(pv0, 2),
                    "Net PV (1%)": _format_number(pv1, 2),
                    "Net PV (2%)": _format_number(pv2, 2),
                    "Drag at 2%": _format_percent(drag2, 2),
                }
            )

    tc_df = pd.DataFrame(tc_rows)
    tc_df = tc_df.rename(
        columns={
            "Net PV (0%)": "Net PV (0\\%)",
            "Net PV (1%)": "Net PV (1\\%)",
            "Net PV (2%)": "Net PV (2\\%)",
            "Drag at 2%": "Drag at 2\\%",
        }
    )
    
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
        "Net terminal portfolio value under proportional transaction costs at 10\\% risk budget. Net PV values are from \\texttt{Transaction Cost.xlsx}. Drag at 2\\% shows the percentage change in terminal value relative to 0\\% costs.",
        "tab:tc-summary",
        tc_tab,
    )

    # --- Appendix: terminal PV grids for each transaction-cost scenario (fixed: gross PV from Metrics/PV.xlsx) ---
    def grid_table(tc_label: str, metric: str, filename: str, caption: str, label: str) -> None:
        rows = []
        for freq in FREQ_ORDER:
            for risk in RISK_ORDER:
                cfg = Config(tc_label, risk, freq)
                if cfg not in configs:
                    continue
                df = read_metric(output_root, cfg, metric)
                # terminal value: last row
                terminal = df.dropna().tail(1).iloc[0]
                row = {"Frequency": freq, "Risk": risk}
                for strat in STRATEGY_ORDER:
                    if strat in terminal.index:
                        row[latex_escape_text(strat)] = float(terminal[strat])
                rows.append(row)
        g = pd.DataFrame(rows)
        g = g.sort_values(["Frequency", "Risk"], key=lambda s: s.map({v: i for i, v in enumerate(FREQ_ORDER + RISK_ORDER)}).fillna(999))

        # format
        g["Risk"] = g["Risk"].map(latex_escape_text)
        for strat in [latex_escape_text(s) for s in STRATEGY_ORDER]:
            if strat in g.columns:
                g[strat] = g[strat].map(lambda x: _format_number(x, 2))

        tab = g.to_latex(index=False, escape=False)
        write_table(tables_root / filename, caption, label, tab)

    def grid_table_reduced(
        tc_label: str,
        metric: str,
        filename: str,
        caption: str,
        label: str,
        *,
        reducer: str,
        decimals: int,
    ) -> None:
        rows = []
        for freq in FREQ_ORDER:
            for risk in RISK_ORDER:
                cfg = Config(tc_label, risk, freq)
                if cfg not in configs:
                    continue
                df = read_metric(output_root, cfg, metric)
                row = {"Frequency": freq, "Risk": risk}
                for strat in STRATEGY_ORDER:
                    if strat in df.columns:
                        row[latex_escape_text(strat)] = _reduce_metric_series(df[strat], reducer)
                rows.append(row)

        g = pd.DataFrame(rows)
        if len(g) == 0:
            return

        g = g.sort_values(["Frequency", "Risk"], key=lambda s: s.map({v: i for i, v in enumerate(FREQ_ORDER + RISK_ORDER)}).fillna(999))
        g["Risk"] = g["Risk"].map(latex_escape_text)
        for strat in [latex_escape_text(s) for s in STRATEGY_ORDER]:
            if strat in g.columns:
                g[strat] = g[strat].map(lambda x: _format_number(x, decimals))

        tab = g.to_latex(index=False, escape=False)
        write_table(tables_root / filename, caption, label, tab)

    grid_table(
        "0% Transaction Cost",
        "PV",
        "appendix_terminal_pv_zero_cost.tex",
        "Terminal portfolio value (0\\% transaction costs) for all risk budgets and rebalancing schedules.",
        "tab:app-terminal-pv-0",
    )

    grid_table_reduced(
        "0% Transaction Cost",
        "MDD",
        "appendix_mdd_zero_cost.tex",
        "Worst within-period maximum drawdown (percent) over time for all risk budgets and rebalancing schedules at 0\\% transaction costs.",
        "tab:app-mdd-0",
        reducer="min",
        decimals=2,
    )

    grid_table_reduced(
        "0% Transaction Cost",
        "Sharpe",
        "appendix_sharpe_zero_cost.tex",
        "Mean Sharpe ratio over time for all risk budgets and rebalancing schedules at 0\\% transaction costs.",
        "tab:app-sharpe-0",
        reducer="mean",
        decimals=3,
    )

    # Additional appendix grids (0% transaction cost): mean realized metrics over time
    grid_table_reduced(
        "0% Transaction Cost",
        "Volatility",
        "appendix_volatility_zero_cost.tex",
        "Mean realized annualized volatility (percent) over time for all risk budgets and rebalancing schedules at 0\\% transaction costs.",
        "tab:app-vol-0",
        reducer="mean",
        decimals=2,
    )
    grid_table_reduced(
        "0% Transaction Cost",
        "MAD",
        "appendix_mad_zero_cost.tex",
        "Mean realized annualized MAD (percent) over time for all risk budgets and rebalancing schedules at 0\\% transaction costs.",
        "tab:app-mad-0",
        reducer="mean",
        decimals=2,
    )
    grid_table_reduced(
        "0% Transaction Cost",
        "IQR",
        "appendix_iqr_zero_cost.tex",
        "Mean realized annualized IQR (percent) over time for all risk budgets and rebalancing schedules at 0\\% transaction costs.",
        "tab:app-iqr-0",
        reducer="mean",
        decimals=2,
    )
    grid_table_reduced(
        "0% Transaction Cost",
        "Sharpe_MAD",
        "appendix_sharpe_mad_zero_cost.tex",
        "Mean Sharpe$_{\\mathrm{MAD}}$ over time for all risk budgets and rebalancing schedules at 0\\% transaction costs.",
        "tab:app-sharpe-mad-0",
        reducer="mean",
        decimals=3,
    )
    grid_table_reduced(
        "0% Transaction Cost",
        "Sharpe_IQR",
        "appendix_sharpe_iqr_zero_cost.tex",
        "Mean Sharpe$_{\\mathrm{IQR}}$ over time for all risk budgets and rebalancing schedules at 0\\% transaction costs.",
        "tab:app-sharpe-iqr-0",
        reducer="mean",
        decimals=3,
    )

    # Additional appendix grids (0% transaction cost): RAR metrics (percent units) reported by the backtest
    grid_table_reduced(
        "0% Transaction Cost",
        "RAR_Vol",
        "appendix_rar_vol_zero_cost.tex",
        "Mean risk-adjusted return (volatility-based, percent) over time for all risk budgets and rebalancing schedules at 0\\% transaction costs.",
        "tab:app-rar-vol-0",
        reducer="mean",
        decimals=3,
    )
    grid_table_reduced(
        "0% Transaction Cost",
        "RAR_MAD",
        "appendix_rar_mad_zero_cost.tex",
        "Mean risk-adjusted return (MAD-based, percent) over time for all risk budgets and rebalancing schedules at 0\\% transaction costs.",
        "tab:app-rar-mad-0",
        reducer="mean",
        decimals=3,
    )
    grid_table_reduced(
        "0% Transaction Cost",
        "RAR_IQR",
        "appendix_rar_iqr_zero_cost.tex",
        "Mean risk-adjusted return (IQR-based, percent) over time for all risk budgets and rebalancing schedules at 0\\% transaction costs.",
        "tab:app-rar-iqr-0",
        reducer="mean",
        decimals=3,
    )

    # Appendix: net terminal PV by transaction cost (from Transaction Cost.xlsx)
    def net_pv_grid(tc_label: str, filename: str, caption: str, label: str) -> None:
        rows = []
        for freq in FREQ_ORDER:
            for risk in RISK_ORDER:
                cfg = Config(tc_label, risk, freq)
                if cfg not in configs:
                    continue
                net = terminal_net_pv(output_root, cfg)
                row = {"Frequency": freq, "Risk": risk}
                for strat in STRATEGY_ORDER:
                    if strat in net.index:
                        row[latex_escape_text(strat)] = float(net[strat])
                rows.append(row)
        g = pd.DataFrame(rows)
        g["Risk"] = g["Risk"].map(latex_escape_text)
        for strat in [latex_escape_text(s) for s in STRATEGY_ORDER]:
            if strat in g.columns:
                g[strat] = g[strat].map(lambda x: _format_number(x, 2))
        tab = g.to_latex(index=False, escape=False)
        write_table(tables_root / filename, caption, label, tab)

    # Appendix: mean turnover grid (from Weights/Comparison.xlsx)
    def turnover_grid(tc_label: str, filename: str, caption: str, label: str) -> None:
        rows = []
        for freq in FREQ_ORDER:
            for risk in RISK_ORDER:
                cfg = Config(tc_label, risk, freq)
                if cfg not in configs:
                    continue
                turnover = read_turnover(output_root, cfg)
                row = {"Frequency": freq, "Risk": risk}
                for strat in STRATEGY_ORDER:
                    if strat in turnover.columns:
                        row[latex_escape_text(strat)] = _reduce_metric_series(turnover[strat], "mean")
                rows.append(row)

        g = pd.DataFrame(rows)
        if len(g) == 0:
            return

        g = g.sort_values(["Frequency", "Risk"], key=lambda s: s.map({v: i for i, v in enumerate(FREQ_ORDER + RISK_ORDER)}).fillna(999))
        g["Risk"] = g["Risk"].map(latex_escape_text)
        for strat in [latex_escape_text(s) for s in STRATEGY_ORDER]:
            if strat in g.columns:
                g[strat] = g[strat].map(lambda x: _format_number(x, 3))
        tab = g.to_latex(index=False, escape=False)
        write_table(tables_root / filename, caption, label, tab)

    turnover_grid(
        "0% Transaction Cost",
        "appendix_turnover_zero_cost.tex",
        "Mean one-way turnover per rebalance for all risk budgets and rebalancing schedules at 0\\% transaction costs.",
        "tab:app-turnover-0",
    )

    net_pv_grid(
        "0% Transaction Cost",
        "appendix_net_pv_tc0.tex",
        "Net terminal portfolio value at 0\\% transaction costs for all risk budgets and rebalancing schedules.",
        "tab:app-netpv-0",
    )
    net_pv_grid(
        "1% Transaction Cost",
        "appendix_net_pv_tc1.tex",
        "Net terminal portfolio value at 1\\% transaction costs for all risk budgets and rebalancing schedules.",
        "tab:app-netpv-1",
    )
    net_pv_grid(
        "2% Transaction Cost",
        "appendix_net_pv_tc2.tex",
        "Net terminal portfolio value at 2\\% transaction costs for all risk budgets and rebalancing schedules.",
        "tab:app-netpv-2",
    )

    # --- Inference: bootstrap CIs (10% risk, 6mo & 1y, 0% cost) ---
    def bootstrap_inference_10pct() -> None:
        risk = "10.00%"
        freqs = ["6mo", "1y"]
        compare_to = "Volatility"
        strategies = ["MAD", "IQR", "95%"]

        tc_labels = ["0% Transaction Cost", "1% Transaction Cost", "2% Transaction Cost"]

        rows = []
        takeaway_rows = []
        for tc_label in tc_labels:
            for freq in freqs:
                cfg = Config(tc_label, risk, freq)
                if cfg not in configs:
                    continue

                period_days = FREQ_TRADING_DAYS.get(freq)
                if period_days is None:
                    continue

                tc_book = read_transaction_cost_book(output_root, cfg)

                def period_returns_for(strategy: str) -> pd.Series:
                    if (strategy, "Invested") not in tc_book.columns or (strategy, "Net Invested") not in tc_book.columns:
                        return pd.Series(dtype=float)
                    invested = tc_book[(strategy, "Invested")].astype(float)
                    net = tc_book[(strategy, "Net Invested")].astype(float)
                    r = (net / invested) - 1.0
                    r = r.replace([math.inf, -math.inf], pd.NA).dropna()
                    # Drop the first row (often a placeholder period in the backtest outputs)
                    if len(r) > 0:
                        r = r.iloc[1:]
                    return r

                base_r = period_returns_for(compare_to)
                if len(base_r) == 0:
                    continue

                # Block length: 2 for 6mo to allow some dependence; 1 for 1y.
                block_len = 2 if freq == "6mo" else 1
                n_boot = 2000

                ann_stat = lambda s: _annualized_return_from_period_returns(s, period_days=period_days)
                sh_stat = lambda s: _annualized_sharpe_from_period_returns(s, period_days=period_days)

                for strat in strategies:
                    strat_r = period_returns_for(strat)
                    if len(strat_r) == 0:
                        continue

                    ann_point, ann_lo, ann_hi = _bootstrap_ci(
                        strat_r,
                        base_r,
                        statistic=ann_stat,
                        n_boot=n_boot,
                        block_len=block_len,
                        seed=12345,
                    )
                    sh_point, sh_lo, sh_hi = _bootstrap_ci(
                        strat_r,
                        base_r,
                        statistic=sh_stat,
                        n_boot=n_boot,
                        block_len=block_len,
                        seed=54321,
                    )

                    rows.append(
                        {
                            "TC": tc_label,
                            "Frequency": freq,
                            "Comparison": f"{strat} - {compare_to}",
                            "Δ AnnReturn": ann_point,
                            "CI AnnReturn": f"[{_format_percent(ann_lo, 2)}, {_format_percent(ann_hi, 2)}]",
                            "Δ Sharpe": sh_point,
                            "CI Sharpe": f"[{_format_number(sh_lo, 3)}, {_format_number(sh_hi, 3)}]",
                        }
                    )

                    takeaway_rows.append(
                        {
                            "TC": tc_label,
                            "Frequency": freq,
                            "Comparison": f"{strat} - {compare_to}",
                            "ann_lo": ann_lo,
                            "ann_hi": ann_hi,
                            "sh_lo": sh_lo,
                            "sh_hi": sh_hi,
                        }
                    )

        if not rows:
            return

        df = pd.DataFrame(rows)
        df["TC"] = df["TC"].map(latex_escape_text)
        df["Frequency"] = df["Frequency"].map(latex_escape_text)
        df["Comparison"] = df["Comparison"].map(latex_escape_text)
        df["Δ AnnReturn"] = df["Δ AnnReturn"].map(lambda x: _format_percent(x, 2))
        df["Δ Sharpe"] = df["Δ Sharpe"].map(lambda x: _format_number(x, 3))

        tab = df[["TC", "Frequency", "Comparison", "Δ AnnReturn", "CI AnnReturn", "Δ Sharpe", "CI Sharpe"]].to_latex(
            index=False,
            escape=False,
        )
        write_table(
            tables_root / "inference_bootstrap_10pct.tex",
            "Moving-block bootstrap (95\\% CI) for differences in annualized return and an annualized Sharpe proxy versus the volatility-constrained strategy at 10\\% risk budget. Net-of-cost holding-period returns are computed from the backtest transaction-cost ledger. Period returns are resampled in blocks (length 2 for 6mo; length 1 for 1y).",
            "tab:bootstrap-10pct",
            tab,
        )

        # Auto-generate a compact interpretive paragraph based on whether CIs exclude 0.
        take = pd.DataFrame(takeaway_rows)

        def _sig_label(lo: float, hi: float) -> str:
            if pd.isna(lo) or pd.isna(hi):
                return "inconclusive"
            if lo > 0:
                return "positive"
            if hi < 0:
                return "negative"
            return "indistinguishable"

        lines = []
        lines.append("\\paragraph{How to read the table.} If a 95\\% CI for $\\Delta$ annualized return (or $\\Delta$ Sharpe) excludes 0, the difference is statistically distinguishable under the moving-block bootstrap. If the CI includes 0, the result is statistically indistinguishable at that level. Economic significance should be judged by the magnitude of $\\Delta$ annualized return and whether it survives transaction costs.")

        for tc_label in tc_labels:
            sub = take[take["TC"] == tc_label]
            if len(sub) == 0:
                continue
            for freq in freqs:
                sf = sub[sub["Frequency"] == freq]
                if len(sf) == 0:
                    continue
                ann_counts = sf.apply(lambda r: _sig_label(r["ann_lo"], r["ann_hi"]), axis=1).value_counts().to_dict()
                sh_counts = sf.apply(lambda r: _sig_label(r["sh_lo"], r["sh_hi"]), axis=1).value_counts().to_dict()
                lines.append(
                    f"\\paragraph{{Summary at {latex_escape_text(tc_label)} ({latex_escape_text(freq)})}} "
                    f"$\\Delta$ annualized return: {ann_counts.get('positive', 0)} positive, {ann_counts.get('negative', 0)} negative, {ann_counts.get('indistinguishable', 0)} indistinguishable. "
                    f"$\\Delta$ Sharpe: {sh_counts.get('positive', 0)} positive, {sh_counts.get('negative', 0)} negative, {sh_counts.get('indistinguishable', 0)} indistinguishable."
                )

        (tables_root / "inference_bootstrap_10pct_takeaways.tex").write_text("\n\n".join(lines) + "\n")

    bootstrap_inference_10pct()

    print(f"Wrote tables to: {tables_root}")


def main() -> None:
    project_root = Path(__file__).resolve().parents[3]
    build_tables(project_root)


if __name__ == "__main__":
    main()
