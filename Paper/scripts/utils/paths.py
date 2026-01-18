from __future__ import annotations

from pathlib import Path


def project_root() -> Path:
    """Return repository root (directory containing Output/, Data/, Paper/)."""
    # paths.py -> utils/ -> scripts/ -> Paper/ -> <project root>
    return Path(__file__).resolve().parents[3]


PROJECT_ROOT = project_root()
PAPER_ROOT = PROJECT_ROOT / "Paper"
SCRIPTS_ROOT = PAPER_ROOT / "scripts"
LATEX_ROOT = PAPER_ROOT / "LaTeX"
TABLES_ROOT = LATEX_ROOT / "tables"
FIGURES_ROOT = LATEX_ROOT / "figures"
OUTPUT_ROOT = PROJECT_ROOT / "Output"
DATA_ROOT = PROJECT_ROOT / "Data"
