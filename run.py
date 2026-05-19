from src.services.gmail_auth import get_gmail_service


def main() -> None:
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


if __name__ == "__main__":
    main()
