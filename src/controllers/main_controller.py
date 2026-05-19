from __future__ import annotations

from PyQt6.QtCore import QObject

from src.services.gmail_auth import get_gmail_service
from src.services.gmail_service import listar_emails, pegar_email_logado, quantidade_total


class MainController(QObject):
    def __init__(self, window) -> None:
        super().__init__()
        self.window = window
        self.gmail_service = None

        self.window.connect_button.clicked.connect(self.connect_gmail)
        self.window.load_emails_button.clicked.connect(self.load_emails)

    def connect_gmail(self) -> None:
        self.window.set_status("Conectando ao Gmail...")
        self.window.set_buttons_enabled(connect=False, load=False)

        try:
            self.gmail_service = get_gmail_service()
            email_address = pegar_email_logado(self.gmail_service)
            total_messages = quantidade_total(self.gmail_service)
        except FileNotFoundError as error:
            self.gmail_service = None
            self.window.set_status(str(error))
            self.window.set_buttons_enabled(connect=True, load=False)
            return
        except Exception as error:
            self.gmail_service = None
            self.window.set_status(f"Erro ao conectar: {error}")
            self.window.set_buttons_enabled(connect=True, load=False)
            return

        self.window.set_status(
            f"Conectado: {email_address} | Total de mensagens: {total_messages}"
        )
        self.window.set_buttons_enabled(connect=True, load=True)

    def load_emails(self) -> None:
        if self.gmail_service is None:
            self.window.set_status("Conecte ao Gmail antes de carregar emails.")
            return

        self.window.set_status("Carregando emails...")
        self.window.set_buttons_enabled(connect=False, load=False)

        try:
            emails = listar_emails(self.gmail_service, limite=10)
        except Exception as error:
            self.window.set_status(f"Erro ao carregar emails: {error}")
            self.window.set_buttons_enabled(connect=True, load=True)
            return

        self.window.show_emails(emails)
        self.window.set_status(f"{len(emails)} emails carregados.")
        self.window.set_buttons_enabled(connect=True, load=True)
