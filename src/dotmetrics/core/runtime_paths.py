from __future__ import annotations

import os
import sys
from pathlib import Path


APP_NAME = "DotMetrics"



def project_root() -> Path:
    return Path(__file__).resolve().parents[3]



def source_root() -> Path:
    return Path(__file__).resolve().parents[2]



def bundle_root() -> Path:
    return Path(getattr(sys, "_MEIPASS", project_root()))



def is_frozen() -> bool:
    return bool(getattr(sys, "frozen", False))



def user_data_dir() -> Path:
    override = os.getenv("DOTMETRICS_DATA_DIR")
    if override:
        base = Path(override)
    elif sys.platform.startswith("win"):
        base = Path(os.getenv("LOCALAPPDATA", Path.home() / "AppData" / "Local"))
    else:
        base = Path(os.getenv("XDG_DATA_HOME", Path.home() / ".local" / "share"))
    path = base if override else base / APP_NAME
    path.mkdir(parents=True, exist_ok=True)
    return path



def logs_dir() -> Path:
    path = user_data_dir() / "logs"
    path.mkdir(parents=True, exist_ok=True)
    return path



def runtime_dir() -> Path:
    path = user_data_dir() / "runtime"
    path.mkdir(parents=True, exist_ok=True)
    return path



def temp_dir() -> Path:
    path = runtime_dir() / "temp"
    path.mkdir(parents=True, exist_ok=True)
    return path



def resource_candidates(relative_path: str | Path) -> list[Path]:
    relative = Path(relative_path)
    return [
        bundle_root() / relative,
        project_root() / relative,
        Path.cwd() / relative,
        user_data_dir() / relative,
    ]



def resolve_resource(relative_path: str | Path) -> Path | None:
    for candidate in resource_candidates(relative_path):
        if candidate.exists():
            return candidate
    return None



def resolve_model_path(filename: str = "yolov8n-DotMetrics.pt", override: str | Path | None = None) -> Path | None:
    configured_path = override or os.getenv("DOTMETRICS_MODEL_PATH")
    if configured_path:
        override_path = Path(configured_path).expanduser()
        if override_path.exists():
            return override_path

    return resolve_resource(Path("models") / filename)
