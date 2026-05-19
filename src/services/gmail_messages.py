from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class EmailPreview:
    message_id: str
    sender: str
    subject: str
    date: str
    snippet: str


def list_email_previews(service, max_results: int = 10) -> list[EmailPreview]:
    response = (
        service.users()
        .messages()
        .list(userId="me", maxResults=max_results, labelIds=["INBOX"])
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

        previews.append(
            EmailPreview(
                message_id=message_data["id"],
                sender=headers.get("From", "(sem remetente)"),
                subject=headers.get("Subject", "(sem assunto)"),
                date=headers.get("Date", "(sem data)"),
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
