import sys

from src.services.gmail_auth import get_gmail_service
from src.services.gmail_messages import list_email_previews


EMAIL_PREVIEW_LIMIT = 10


def main() -> None:
    _configure_stdout()

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


def _configure_stdout() -> None:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")


if __name__ == "__main__":
    main()
