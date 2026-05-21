from __future__ import annotations

from src.services.email_service import EmailPreview, list_email_previews


def listar_emails(
    service,
    limite: int = 10,
    label_ids: list[str] | None = None,
) -> list[EmailPreview]:
    return list_email_previews(
        service,
        max_results=limite,
        label_ids=label_ids,
    )


def pegar_assunto(email: EmailPreview) -> str:
    return email.subject


def pegar_remetente(email: EmailPreview) -> str:
    return email.sender


def pegar_data(email: EmailPreview) -> str:
    return email.date


def quantidade_total(service) -> int:
    profile = service.users().getProfile(userId="me").execute()
    return int(profile.get("messagesTotal", 0))


def pegar_email_logado(service) -> str:
    profile = service.users().getProfile(userId="me").execute()
    return profile.get("emailAddress", "conta desconhecida")
