"""Test package for kliamka.

Ensure tests import the repository-under-test from the local ``src/`` tree
instead of any globally installed ``kliamka`` distribution.
"""

from __future__ import annotations

import sys
from pathlib import Path

_SRC_PATH = Path(__file__).resolve().parents[1] / "src"

if str(_SRC_PATH) not in sys.path:
    sys.path.insert(0, str(_SRC_PATH))
