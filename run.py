"""Command-line entry point for Gmail Cleaner."""

import sys

from src.services.gmail_auth import get_gmail_service
from src.services.gmail_filters import find_old_emails, find_repeated_senders
from src.services.gmail_messages import list_email_previews


EMAIL_PREVIEW_LIMIT = 10
EMAIL_ANALYSIS_LIMIT = 100
OLD_EMAIL_DAYS = 365
REPEATED_SENDER_MIN_COUNT = 2
APP_NAME = "Gmail Cleaner"


def main() -> None:
    _configure_stdout()
    print(f"{APP_NAME}\n")

    try:
        service = get_gmail_service()
    except FileNotFoundError as error:
        print(error)
        return

    profile = service.users().getProfile(userId="me").execute()

    email_address = profile.get("emailAddress", "conta desconhecida")
    total_messages = profile.get("messagesTotal", 0)

    print(f"Login realizado com sucesso: {email_address}")
    print(f"Total de mensagens na conta: {total_messages}")

    emails = list_email_previews(service, max_results=EMAIL_PREVIEW_LIMIT)
    if not emails:
        print("Nenhum email encontrado na caixa de entrada.")
        return

    print(f"\nPrimeiros {len(emails)} emails da caixa de entrada:\n")
    for index, email in enumerate(emails, start=1):
        print(f"{index}. {email.subject}")
        print(f"   De: {email.sender}")
        print(f"   Data: {email.date}")
        print(f"   Preview: {email.snippet}\n")

    analysis_emails = list_email_previews(service, max_results=EMAIL_ANALYSIS_LIMIT)
    repeated_senders = find_repeated_senders(
        analysis_emails,
        min_count=REPEATED_SENDER_MIN_COUNT,
    )
    old_emails = find_old_emails(analysis_emails, older_than_days=OLD_EMAIL_DAYS)

    print(f"Analise dos primeiros {len(analysis_emails)} emails da caixa de entrada:")
    print("\nRemetentes repetidos:")
    if repeated_senders:
        for sender in repeated_senders[:10]:
            print(f"- {sender.sender_email}: {sender.count} emails")
            print(f"  Ultimo assunto: {sender.latest_subject}")
    else:
        print("- Nenhum remetente repetido encontrado.")

    print(f"\nEmails com mais de {OLD_EMAIL_DAYS} dias:")
    if old_emails:
        for email in old_emails[:10]:
            date = email.received_at.date().isoformat() if email.received_at else email.date
            print(f"- {date} | {email.sender_email} | {email.subject}")
    else:
        print("- Nenhum email antigo encontrado no lote analisado.")


def _configure_stdout() -> None:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")


if __name__ == "__main__":
    main()
