"""Compatibility wrapper for table generation.

The canonical implementation lives in `Paper/scripts/build_paper_tables.py`.
This wrapper keeps existing entrypoints working:
- `python Paper/scripts/build_all.py` (which imports from Paper/scripts/tables)
- `python Paper/scripts/tables/build_paper_tables.py`

Preferred usage going forward:
- `python -m Paper.scripts.build_paper_tables`
"""

from __future__ import annotations

if __package__ is None or __package__ == "":
    import sys
    from pathlib import Path

    sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

from Paper.scripts.build_paper_tables import build_tables, main

__all__ = ["build_tables", "main"]


if __name__ == "__main__":
    main()
