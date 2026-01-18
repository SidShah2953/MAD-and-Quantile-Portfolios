from __future__ import annotations

from pathlib import Path

import pandas as pd

from .constants import Config, FREQ_ORDER, RISK_ORDER, TC_ORDER


def discover_configs(output_root: Path) -> list[Config]:
    """Discover which (tc, risk, freq) combinations exist under Output/."""
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
    return pd.read_excel(path, index_col=0)


def read_weights(output_root: Path, cfg: Config, strategy: str) -> pd.DataFrame:
    path = output_root / cfg.tc_label / cfg.risk_label / cfg.freq_label / "Weights" / f"{strategy}.xlsx"
    return pd.read_excel(path, index_col=0)


def read_turnover(output_root: Path, cfg: Config) -> pd.DataFrame:
    path = output_root / cfg.tc_label / cfg.risk_label / cfg.freq_label / "Weights" / "Comparison.xlsx"
    return pd.read_excel(path, index_col=0)


def read_transaction_cost_book(output_root: Path, cfg: Config) -> pd.DataFrame:
    path = output_root / cfg.tc_label / cfg.risk_label / cfg.freq_label / "Transaction Cost.xlsx"
    return pd.read_excel(path, header=[0, 1], index_col=0)
