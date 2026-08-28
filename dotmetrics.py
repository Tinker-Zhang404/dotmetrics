from __future__ import annotations

import sys
from pathlib import Path



def _ensure_source_root() -> None:
    root = Path(__file__).resolve().parent
    src_root = root / "src"
    for path in (str(root), str(src_root)):
        if path not in sys.path:
            sys.path.insert(0, path)



def main() -> int:
    _ensure_source_root()
    try:
        from dotmetrics.app import main as package_main
    except ImportError:
        from src.dotmetrics.app import main as package_main

    return package_main()


if __name__ == "__main__":
    raise SystemExit(main())
