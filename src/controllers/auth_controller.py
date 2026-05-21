from __future__ import annotations

from src.auth.oauth import get_gmail_service
from src.auth.token_manager import remove_local_token


class AuthController:
    def connect(self):
        return get_gmail_service()

    def remove_local_token(self) -> bool:
        return remove_local_token()
