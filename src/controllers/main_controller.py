from __future__ import annotations

from PyQt6.QtCore import QObject

from src.services.gmail_actions import (
    buscar_emails_por_remetente,
    mover_emails_para_lixeira,
)
from src.services.gmail_service import (
    pegar_email_logado,
    quantidade_total,
)


class MainController(QObject):
    def __init__(self, window) -> None:
        super().__init__()
        self.window = window
        self.gmail_service = None
        self.message_ids = []

        self.window.connect_button.clicked.connect(self.connect_gmail)
        self.window.search_button.clicked.connect(self.search_sender)
        self.window.trash_button.clicked.connect(self.move_found_to_trash)

    def connect_gmail(self) -> None:
        from src.services.gmail_auth import get_gmail_service

        self.window.set_status("Conectando ao Gmail...")
        self.window.set_buttons_enabled(connect=False, search=False)

        try:
            self.gmail_service = get_gmail_service()
            email_address = pegar_email_logado(self.gmail_service)
            total_messages = quantidade_total(self.gmail_service)
        except FileNotFoundError as error:
            self.gmail_service = None
            self.window.set_status(str(error))
            self.window.set_buttons_enabled(connect=True, search=False)
            return
        except Exception as error:
            self.gmail_service = None
            self.window.set_status(f"Erro ao conectar: {error}")
            self.window.set_buttons_enabled(connect=True, search=False)
            return

        self.window.set_status(
            f"Conectado: {email_address} | Total de mensagens: {total_messages}"
        )
        self.window.set_buttons_enabled(connect=True, search=True)

    def search_sender(self) -> None:
        if self.gmail_service is None:
            self.window.set_status("Conecte ao Gmail antes de buscar.")
            return

        remetente = self.window.get_sender()
        if not remetente:
            self.window.set_status("Digite um remetente para buscar.")
            return

        self.window.set_status("Buscando e-mails...")
        self.window.reset_result()
        self.window.set_buttons_enabled(connect=False, search=False)

        try:
            self.message_ids = buscar_emails_por_remetente(self.gmail_service, remetente)
        except Exception as error:
            self.message_ids = []
            self.window.set_status(f"Erro ao buscar e-mails: {error}")
            self.window.set_buttons_enabled(connect=True, search=True)
            return

        total = len(self.message_ids)
        self.window.show_result(remetente, total)
        self.window.set_status(f"{total} e-mail(s) encontrado(s).")
        self.window.set_buttons_enabled(connect=True, search=True, trash=total > 0)

    def move_found_to_trash(self) -> None:
        if self.gmail_service is None:
            self.window.set_status("Conecte ao Gmail antes de mover emails.")
            return

        if not self.message_ids:
            self.window.set_status("Busque um remetente antes de mover para a lixeira.")
            return

        if not self.window.confirm_move_to_trash(len(self.message_ids)):
            self.window.set_status("Operacao cancelada.")
            return

        self.window.set_status("Movendo email(s) para a lixeira...")
        self.window.set_buttons_enabled(connect=False, search=False, trash=False)

        try:
            moved_count = mover_emails_para_lixeira(self.gmail_service, self.message_ids)
        except Exception as error:
            self.window.set_status(f"Erro ao mover para a lixeira: {error}")
            self.window.set_buttons_enabled(connect=True, search=True, trash=True)
            return

        self.message_ids = []
        self.window.reset_result()
        self.window.set_status(f"{moved_count} e-mail(s) movido(s) para a lixeira.")
        self.window.set_buttons_enabled(connect=True, search=True)
