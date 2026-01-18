from __future__ import annotations

import sys
from pathlib import Path


def ensure_project_root_on_path(current_file: str) -> None:
    """Ensure repo root is on sys.path for script-style execution.

    This keeps scripts runnable via e.g. `python Paper/scripts/build_all.py` while
    still allowing clean absolute imports like `from Paper.scripts...`.
    """
    root = Path(current_file).resolve().parents[2]  # Paper/scripts/<file>.py -> repo root
    root_str = str(root)
    if root_str not in sys.path:
        sys.path.insert(0, root_str)
