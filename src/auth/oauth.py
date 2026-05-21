from __future__ import annotations

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

from src.config.settings import CLIENT_SECRET_FILE, GMAIL_SCOPES, TOKEN_FILE
from src.auth.token_manager import remove_local_token


def get_gmail_credentials() -> Credentials:
    credentials = None

    if TOKEN_FILE.exists():
        credentials = Credentials.from_authorized_user_file(
            str(TOKEN_FILE),
            GMAIL_SCOPES,
        )

    if credentials and not credentials.has_scopes(GMAIL_SCOPES):
        credentials = None

    if credentials and credentials.valid:
        return credentials

    if credentials and credentials.expired and credentials.refresh_token:
        credentials.refresh(Request())
    else:
        if not CLIENT_SECRET_FILE.exists():
            raise FileNotFoundError(
                "Arquivo de credenciais nao encontrado. "
                f"Coloque o OAuth client em: {CLIENT_SECRET_FILE}"
            )

        flow = InstalledAppFlow.from_client_secrets_file(
            str(CLIENT_SECRET_FILE),
            GMAIL_SCOPES,
        )
        credentials = flow.run_local_server(
            port=0,
            authorization_prompt_message=(
                "Abra este link para fazer login no Gmail:\n{url}\n"
            ),
            success_message=(
                "Login concluido. Pode fechar esta aba e voltar ao terminal."
            ),
        )

    TOKEN_FILE.parent.mkdir(parents=True, exist_ok=True)
    TOKEN_FILE.write_text(credentials.to_json(), encoding="utf-8")

    return credentials


def get_gmail_service():
    credentials = get_gmail_credentials()
    return build("gmail", "v1", credentials=credentials)
