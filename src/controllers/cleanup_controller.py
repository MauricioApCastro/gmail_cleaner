from __future__ import annotations

from src.services.cleanup_service import mover_emails_para_lixeira


class CleanupController:
    def move_to_trash(
        self, service, message_ids: list[str], progress_callback=None
    ) -> int:
        return mover_emails_para_lixeira(service, message_ids, progress_callback)
