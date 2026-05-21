from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from email.utils import parseaddr


@dataclass(frozen=True)
class EmailPreview:
    message_id: str
    sender: str
    sender_email: str
    subject: str
    date: str
    received_at: datetime | None
    snippet: str


def list_email_previews(
    service,
    max_results: int = 10,
    label_ids: list[str] | None = None,
) -> list[EmailPreview]:
    label_ids = label_ids or ["INBOX"]
    response = (
        service.users()
        .messages()
        .list(userId="me", maxResults=max_results, labelIds=label_ids)
        .execute()
    )
    messages = response.get("messages", [])

    previews = []
    for message in messages:
        message_data = (
            service.users()
            .messages()
            .get(
                userId="me",
                id=message["id"],
                format="metadata",
                metadataHeaders=["From", "Subject", "Date"],
            )
            .execute()
        )
        headers = _headers_to_dict(message_data.get("payload", {}).get("headers", []))
        sender = headers.get("From", "(sem remetente)")

        previews.append(
            EmailPreview(
                message_id=message_data["id"],
                sender=sender,
                sender_email=_extract_sender_email(sender),
                subject=headers.get("Subject", "(sem assunto)"),
                date=headers.get("Date", "(sem data)"),
                received_at=_parse_internal_date(message_data.get("internalDate")),
                snippet=message_data.get("snippet", ""),
            )
        )

    return previews


def _headers_to_dict(headers: list[dict[str, str]]) -> dict[str, str]:
    return {
        header.get("name", ""): header.get("value", "")
        for header in headers
        if header.get("name")
    }


def _extract_sender_email(sender: str) -> str:
    _, email_address = parseaddr(sender)
    return email_address.lower() or sender.strip().lower()


def _parse_internal_date(internal_date: str | None) -> datetime | None:
    if not internal_date:
        return None

    try:
        timestamp = int(internal_date) / 1000
    except ValueError:
        return None

    return datetime.fromtimestamp(timestamp, tz=UTC)
