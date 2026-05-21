from __future__ import annotations

import json
from datetime import UTC, datetime

from src.config.settings import CLEANUP_LOG_FILE
from src.services.cleanup_service import EmailAnalysis


def write_cleanup_log(
    *,
    account_email: str,
    sender_query: str,
    moved_emails: list[EmailAnalysis],
    protected_count: int,
) -> None:
    CLEANUP_LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
    record = {
        "timestamp": datetime.now(UTC).isoformat(),
        "account_email": account_email,
        "sender_query": sender_query,
        "moved_count": len(moved_emails),
        "protected_count": protected_count,
        "estimated_space_bytes": sum(email.size_estimate for email in moved_emails),
        "message_ids": [email.message_id for email in moved_emails],
        "senders": sorted({email.sender_email for email in moved_emails}),
    }
    with CLEANUP_LOG_FILE.open("a", encoding="utf-8") as log_file:
        log_file.write(json.dumps(record, ensure_ascii=False) + "\n")
