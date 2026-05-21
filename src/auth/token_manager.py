from __future__ import annotations

from src.config.settings import TOKEN_FILE


def remove_local_token() -> bool:
    if not TOKEN_FILE.exists():
        return False

    TOKEN_FILE.unlink()
    return True
