from __future__ import annotations

from pathlib import Path

import pandas as pd


def main() -> None:
    base = Path(__file__).resolve().parents[3]
    metrics_file = base / "Output/0% Transaction Cost/10.00%/6mo/Metrics/PV.xlsx"
    print("PV exists:", metrics_file.exists(), metrics_file)
    pv = pd.read_excel(metrics_file, index_col=0)
    print("PV shape:", pv.shape)
    print("PV columns:", list(pv.columns))
    print("PV index sample:", list(pv.index[:3]))
    print("PV last row:\n", pv.tail(1))

    mdd_file = base / "Output/0% Transaction Cost/10.00%/6mo/Metrics/MDD.xlsx"
    mdd = pd.read_excel(mdd_file, index_col=0)
    print("MDD columns:", list(mdd.columns))
    print("MDD last row:\n", mdd.tail(1))
    print("MDD min per column:\n", mdd.min())

    comp_file = base / "Output/0% Transaction Cost/10.00%/6mo/Weights/Comparison.xlsx"
    xls = pd.ExcelFile(comp_file)
    print("Comparison sheets:", xls.sheet_names)
    for sheet in xls.sheet_names:
        df = pd.read_excel(comp_file, sheet_name=sheet, index_col=0)
        print(f"\nSheet: {sheet}")
        print("shape:", df.shape)
        print("columns sample:", list(df.columns)[:12])
        print("tail:\n", df.tail(1))


if __name__ == "__main__":
    main()
