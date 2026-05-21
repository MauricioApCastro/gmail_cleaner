from __future__ import annotations

from src.auth.oauth import get_gmail_service


class GmailProvider:
    def get_service(self):
        return get_gmail_service()
