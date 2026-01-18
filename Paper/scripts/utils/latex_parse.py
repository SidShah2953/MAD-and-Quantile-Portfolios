from __future__ import annotations

import re


def parse_simple_tabular_rows(tex: str) -> list[list[str]]:
    """Parse rows from a simple generated LaTeX tabular.

    Designed for this repo's generated tables (toprule/midrule/bottomrule, no
    complex nested tabulars). Returns list of cell lists.
    """
    rows: list[list[str]] = []
    for line in tex.splitlines():
        line = line.strip()
        if not line or line.startswith("%"):
            continue
        if any(line.startswith(cmd) for cmd in ("\\toprule", "\\midrule", "\\bottomrule")):
            continue
        if line.startswith("\\begin") or line.startswith("\\end"):
            continue
        if "&" not in line or "\\\\" not in line:
            continue

        # strip trailing \\
        line = line.split("\\\\", 1)[0]

        # Split on unescaped & only.
        parts = [p.strip() for p in re.split(r"(?<!\\\\)&", line)]
        parts = [p.replace("\\&", "&").replace("\\%", "%") for p in parts]
        rows.append(parts)

    return rows
