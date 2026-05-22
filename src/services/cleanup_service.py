from __future__ import annotations

from collections import Counter, defaultdict
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime
from email.utils import parseaddr
from base64 import urlsafe_b64decode

ProgressCallback = Callable[[int, int], None]


@dataclass(frozen=True)
class ResultadoBuscaRemetente:
    emails: list["EmailAnalysis"]

    @property
    def total(self) -> int:
        return len(self.emails)

    @property
    def emails_sem_anexo(self) -> list[str]:
        return [email.message_id for email in self.emails if not email.has_attachment]

    @property
    def emails_com_anexo(self) -> list[str]:
        return [email.message_id for email in self.emails if email.has_attachment]


@dataclass(frozen=True)
class EmailAnalysis:
    message_id: str
    sender: str
    sender_email: str
    subject: str
    snippet: str
    body: str
    received_at: datetime | None
    has_attachment: bool
    size_estimate: int
    label_ids: list[str]


@dataclass(frozen=True)
class RemetenteVolume:
    remetente: str
    email: str
    total: int


def listar_remetentes_por_volume(
    service,
    progress_callback: ProgressCallback | None = None,
) -> list[RemetenteVolume]:
    message_ids = []
    page_token = None

    while True:
        request_params = {
            "userId": "me",
            "maxResults": 500,
        }
        if page_token:
            request_params["pageToken"] = page_token

        response = service.users().messages().list(**request_params).execute()
        message_ids.extend(message["id"] for message in response.get("messages", []))

        page_token = response.get("nextPageToken")
        if not page_token:
            break

    total = len(message_ids)
    if progress_callback is not None:
        progress_callback(0, total)

    counts: Counter[str] = Counter()
    display_names: dict[str, Counter[str]] = defaultdict(Counter)

    for index, message_id in enumerate(message_ids, start=1):
        message = (
            service.users()
            .messages()
            .get(
                userId="me",
                id=message_id,
                format="metadata",
                metadataHeaders=["From"],
            )
            .execute()
        )
        remetente = _extrair_header(message, "From") or "(sem remetente)"
        email = _normalizar_remetente(remetente)
        counts[email] += 1
        display_names[email][remetente] += 1

        if progress_callback is not None:
            progress_callback(index, total)

    ranking = [
        RemetenteVolume(
            remetente=display_names[email].most_common(1)[0][0],
            email=email,
            total=count,
        )
        for email, count in counts.items()
    ]
    return sorted(ranking, key=lambda remetente: remetente.total, reverse=True)


def buscar_emails_por_remetente(
    service,
    remetente: str,
    progress_callback: ProgressCallback | None = None,
) -> ResultadoBuscaRemetente:
    remetente = remetente.strip()
    if not remetente:
        raise ValueError("Informe um remetente para buscar.")

    message_ids = []
    page_token = None

    while True:
        request_params = {
            "userId": "me",
            "q": f"from:{remetente}",
            "maxResults": 500,
        }
        if page_token:
            request_params["pageToken"] = page_token

        request = service.users().messages().list(**request_params)
        response = request.execute()
        message_ids.extend(message["id"] for message in response.get("messages", []))
        print(f"Encontrados ate agora: {len(message_ids)}")

        page_token = response.get("nextPageToken")
        if not page_token:
            break

    emails = []

    total = len(message_ids)
    if progress_callback is not None:
        progress_callback(0, total)

    for index, message_id in enumerate(message_ids, start=1):
        print(f"Verificando anexos {index}/{total}...")
        emails.append(_analisar_email(service, message_id))
        if progress_callback is not None:
            progress_callback(index, total)

    return ResultadoBuscaRemetente(emails=emails)


def mover_emails_para_lixeira(
    service,
    message_ids: list[str],
    progress_callback: ProgressCallback | None = None,
) -> int:
    total = len(message_ids)
    if progress_callback is not None:
        progress_callback(0, total)

    for index, message_id in enumerate(message_ids, start=1):
        print(f"Movendo {index}/{total} para a lixeira...")
        service.users().messages().trash(userId="me", id=message_id).execute()
        if progress_callback is not None:
            progress_callback(index, total)

    return total


def definir_email_importante(service, message_id: str, important: bool) -> None:
    body = (
        {"addLabelIds": ["IMPORTANT"], "removeLabelIds": []}
        if important
        else {"addLabelIds": [], "removeLabelIds": ["IMPORTANT"]}
    )
    service.users().messages().modify(
        userId="me",
        id=message_id,
        body=body,
    ).execute()


def _analisar_email(service, message_id: str) -> EmailAnalysis:
    message = (
        service.users()
        .messages()
        .get(userId="me", id=message_id, format="full")
        .execute()
    )
    headers = _headers_to_dict(message.get("payload", {}).get("headers", []))
    sender = headers.get("From", "(sem remetente)")
    payload = message.get("payload", {})

    return EmailAnalysis(
        message_id=message_id,
        sender=sender,
        sender_email=_normalizar_remetente(sender),
        subject=headers.get("Subject", "(sem assunto)"),
        snippet=message.get("snippet", ""),
        body=_extrair_corpo_texto(payload),
        received_at=_parse_internal_date(message.get("internalDate")),
        has_attachment=_payload_tem_anexo(payload),
        size_estimate=int(message.get("sizeEstimate", 0) or 0),
        label_ids=message.get("labelIds", []),
    )


def _extrair_header(message: dict, header_name: str) -> str:
    headers = message.get("payload", {}).get("headers", [])
    for header in headers:
        if header.get("name", "").lower() == header_name.lower():
            return header.get("value", "")
    return ""


def _headers_to_dict(headers: list[dict[str, str]]) -> dict[str, str]:
    return {
        header.get("name", ""): header.get("value", "")
        for header in headers
        if header.get("name")
    }


def _normalizar_remetente(remetente: str) -> str:
    _, email_address = parseaddr(remetente)
    return email_address.lower() or remetente.strip().lower()


def _parse_internal_date(internal_date: str | None) -> datetime | None:
    if not internal_date:
        return None

    try:
        timestamp = int(internal_date) / 1000
    except ValueError:
        return None

    return datetime.fromtimestamp(timestamp, tz=UTC)


def _extrair_corpo_texto(payload: dict) -> str:
    mime_type = payload.get("mimeType", "")
    data = payload.get("body", {}).get("data")
    if data and mime_type in {"text/plain", "text/html"}:
        try:
            return urlsafe_b64decode(data + "=" * (-len(data) % 4)).decode(
                "utf-8",
                errors="ignore",
            )
        except ValueError:
            return ""

    return " ".join(
        text
        for text in (_extrair_corpo_texto(part) for part in payload.get("parts", []))
        if text
    )


def _payload_tem_anexo(payload: dict) -> bool:
    filename = payload.get("filename", "")
    if filename:
        return True

    return any(_payload_tem_anexo(part) for part in payload.get("parts", []))
