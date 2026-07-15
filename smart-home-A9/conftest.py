"""
Repository-wide pytest bootstrap so root-level test runs can import backend modules.
"""
from __future__ import annotations

import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parent
BACKEND_ROOT = ROOT / "cloud" / "backend"

backend_path = str(BACKEND_ROOT)
if backend_path not in sys.path:
    sys.path.insert(0, backend_path)
