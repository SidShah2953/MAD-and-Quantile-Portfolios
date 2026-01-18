from __future__ import annotations

from dataclasses import dataclass


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
