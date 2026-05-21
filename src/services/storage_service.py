from __future__ import annotations

from pathlib import Path

from src.config.settings import DATA_DIR, LOGS_DIR


def ensure_app_storage() -> None:
    for path in (
        DATA_DIR / "accounts",
        DATA_DIR / "exceptions",
        DATA_DIR / "history",
        DATA_DIR / "cache",
        LOGS_DIR,
    ):
        path.mkdir(parents=True, exist_ok=True)


def data_path(*parts: str) -> Path:
    return DATA_DIR.joinpath(*parts)
