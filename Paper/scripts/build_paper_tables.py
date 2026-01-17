from __future__ import annotations

import math
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

import pandas as pd


@dataclass(frozen=True)
class Config:
    tc_label: str  # e.g. "0% Transaction Cost"
    risk_label: str  # e.g. "10.00%"
    freq_label: str  # e.g. "6mo"


STRATEGY_ORDER = ["S&P BnH", "Volatility", "MAD", "IQR", "95%"]
FREQ_ORDER = ["1mo", "3mo", "6mo", "1y"]
RISK_ORDER = ["5.00%", "10.00%", "15.00%"]
TC_ORDER = ["0% Transaction Cost", "1% Transaction Cost", "2% Transaction Cost"]


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
        turnover_mean = _reduce_metric_series(turnover[strat], "mean_excluding_first") if strat in turnover.columns else float("nan")

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
    if reducer == "mean_excluding_first":
        s = s.iloc[1:] if len(s) > 1 else s.iloc[0:0]
        return float(s.mean()) if len(s) else float("nan")
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

    tab = best_df.to_latex(index=False, escape=False, longtable=False)
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
    tc_tab = tc_df.to_latex(index=False, escape=False)
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

    grid_table(
        "0% Transaction Cost",
        "MDD",
        "appendix_mdd_zero_cost.tex",
        "Worst maximum drawdown (percent) for all risk budgets and rebalancing schedules at 0\\% transaction costs.",
        "tab:app-mdd-0",
    )

    grid_table(
        "0% Transaction Cost",
        "Sharpe",
        "appendix_sharpe_zero_cost.tex",
        "Terminal Sharpe ratio values for all risk budgets and rebalancing schedules at 0\\% transaction costs.",
        "tab:app-sharpe-0",
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
                        row[latex_escape_text(strat)] = _reduce_metric_series(turnover[strat], "mean_excluding_first")
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

    print(f"Wrote tables to: {tables_root}")


def main() -> None:
    project_root = Path(__file__).resolve().parents[2]
    build_tables(project_root)


if __name__ == "__main__":
    main()
