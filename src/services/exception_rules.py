from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta


@dataclass(frozen=True)
class ExceptionSettings:
    protected_senders: set[str] = field(default_factory=set)
    protected_domains: set[str] = field(default_factory=set)
    subject_keywords: set[str] = field(default_factory=set)
    body_keywords: set[str] = field(default_factory=set)
    protect_attachments: bool = True
    protect_recent_days: int = 30
    protect_starred_or_important: bool = True


@dataclass(frozen=True)
class EmailProtection:
    message_id: str
    protected: bool
    reason: str = ""


def apply_exception_rules(
    emails: list, settings: ExceptionSettings
) -> list[EmailProtection]:
    return [get_protection(email, settings) for email in emails]


def is_protected_email(email, settings: ExceptionSettings) -> bool:
    return get_protection(email, settings).protected


def get_protection_reason(email, settings: ExceptionSettings) -> str:
    return get_protection(email, settings).reason


def get_protection(email, settings: ExceptionSettings) -> EmailProtection:
    reason = _first_protection_reason(email, settings)
    return EmailProtection(
        message_id=email.message_id,
        protected=bool(reason),
        reason=reason,
    )


def _first_protection_reason(email, settings: ExceptionSettings) -> str:
    sender_email = _normalize(getattr(email, "sender_email", ""))
    sender_domain = _domain_from_email(sender_email)
    subject = _normalize(getattr(email, "subject", ""))
    body = _normalize(getattr(email, "body", "") or getattr(email, "snippet", ""))
    labels = {label.lower() for label in getattr(email, "label_ids", [])}

    if settings.protect_attachments and getattr(email, "has_attachment", False):
        return "Possui anexo"

    if sender_email and sender_email in settings.protected_senders:
        return "Remetente protegido"

    protected_domains = {
        domain if domain.startswith("@") else f"@{domain}"
        for domain in settings.protected_domains
    }
    if sender_domain and sender_domain in protected_domains:
        return "Dominio protegido"

    if _has_keyword(subject, settings.subject_keywords):
        return "Palavra-chave encontrada no assunto"

    if _has_keyword(body, settings.body_keywords):
        return "Palavra-chave encontrada no corpo"

    if _is_recent(getattr(email, "received_at", None), settings.protect_recent_days):
        return "E-mail recente"

    if settings.protect_starred_or_important and (
        "starred" in labels or "important" in labels
    ):
        return "Marcado como importante/estrela"

    return ""


def _has_keyword(text: str, keywords: set[str]) -> bool:
    return any(keyword and keyword in text for keyword in keywords)


def _is_recent(received_at: datetime | None, days: int) -> bool:
    if days <= 0 or received_at is None:
        return False

    return received_at >= datetime.now(UTC) - timedelta(days=days)


def _domain_from_email(email: str) -> str:
    if "@" not in email:
        return ""
    return "@" + email.rsplit("@", 1)[1]


def _normalize(value: str) -> str:
    return value.strip().lower()
