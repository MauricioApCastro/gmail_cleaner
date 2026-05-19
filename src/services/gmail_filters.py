from __future__ import annotations

from collections import Counter, defaultdict
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

from src.services.gmail_messages import EmailPreview


@dataclass(frozen=True)
class SenderGroup:
    sender_email: str
    count: int
    latest_subject: str
    latest_sender: str


def find_repeated_senders(
    emails: list[EmailPreview],
    min_count: int = 2,
) -> list[SenderGroup]:
    counts = Counter(email.sender_email for email in emails if email.sender_email)
    grouped = defaultdict(list)

    for email in emails:
        if email.sender_email:
            grouped[email.sender_email].append(email)

    repeated = []
    for sender_email, count in counts.items():
        if count < min_count:
            continue

        latest_email = _latest_email(grouped[sender_email])
        repeated.append(
            SenderGroup(
                sender_email=sender_email,
                count=count,
                latest_subject=latest_email.subject,
                latest_sender=latest_email.sender,
            )
        )

    return sorted(repeated, key=lambda sender: sender.count, reverse=True)


def find_old_emails(
    emails: list[EmailPreview],
    older_than_days: int = 365,
) -> list[EmailPreview]:
    cutoff = datetime.now(UTC) - timedelta(days=older_than_days)
    old_emails = [
        email
        for email in emails
        if email.received_at is not None and email.received_at < cutoff
    ]

    return sorted(old_emails, key=lambda email: email.received_at or datetime.min)


def _latest_email(emails: list[EmailPreview]) -> EmailPreview:
    return max(
        emails,
        key=lambda email: email.received_at or datetime.min.replace(tzinfo=UTC),
    )
