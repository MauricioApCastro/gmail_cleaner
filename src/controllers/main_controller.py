from __future__ import annotations

from collections import Counter

from PyQt6.QtCore import QObject
from PyQt6.QtWidgets import QApplication

from src.auth.oauth import get_gmail_service
from src.auth.token_manager import remove_local_token
from src.services.history_service import write_cleanup_log
from src.services.exception_rules import apply_exception_rules
from src.services.cleanup_service import (
    EmailAnalysis,
    buscar_emails_por_remetente,
    listar_remetentes_por_volume,
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
        self.total_messages = 0
        self.sender_ranking = []
        self.current_sender_index = 0
        self.current_emails: list[EmailAnalysis] = []
        self.cleanable_message_ids: list[str] = []
        self.protected_count = 0
        self.ranking_mode = False
        self.account_email = ""

        self.window.connect_button.clicked.connect(self.toggle_gmail_connection)
        self.window.search_button.clicked.connect(self.search_sender)
        self.window.rank_button.clicked.connect(self.find_sender_ranking)
        self.window.next_button.clicked.connect(self.search_sender)
        self.window.trash_button.clicked.connect(self.move_found_to_trash)
        self.window.result_table.cellClicked.connect(self.select_sender_from_ranking)
        self._connect_exception_controls()

    def toggle_gmail_connection(self) -> None:
        if self.gmail_service is None:
            self.connect_gmail()
        else:
            self.disconnect_gmail(remove_token=True)

    def connect_gmail(self) -> None:
        self.window.set_status("Conectando ao Gmail...", "searching")
        self.window.show_loading(True)
        self.window.set_buttons_enabled(connect=False, search=False, rank=False)
        QApplication.processEvents()

        try:
            self.gmail_service = get_gmail_service()
            email_address = pegar_email_logado(self.gmail_service)
            self.account_email = email_address
            self.total_messages = quantidade_total(self.gmail_service)
        except FileNotFoundError as error:
            self._clear_state()
            self.window.show_loading(False)
            self.window.set_connected_state(False)
            self.window.set_status(str(error), "error")
            self.window.set_buttons_enabled(connect=True, search=False)
            return
        except Exception as error:
            self._clear_state()
            self.window.show_loading(False)
            self.window.set_connected_state(False)
            self.window.set_status(f"Erro ao conectar: {error}", "error")
            self.window.set_buttons_enabled(connect=True, search=False)
            return

        self.current_sender_index = 0
        self.sender_ranking = []
        self.current_emails = []
        self.cleanable_message_ids = []
        self.protected_count = 0
        self.ranking_mode = False

        self.window.show_summary(
            {
                "total_messages": self.total_messages,
                "found": 0,
                "cleanable": "A analisar",
                "protected": 0,
                "unique_senders": "A analisar",
                "estimated_space": "A analisar",
            }
        )
        self.window.show_loading(False)
        self.window.set_status(
            f"Conectado: {email_address} | Digite um remetente para buscar.",
            "connected",
        )
        self.window.set_connected_state(True)
        self.window.set_buttons_enabled(connect=True, search=True, rank=True)

    def disconnect_gmail(self, remove_token: bool = False) -> None:
        removed = remove_local_token() if remove_token else False
        self._clear_state()
        self.window.show_loading(False)
        self.window.reset_result()
        self.window.set_sender("")
        self.window.set_connected_state(False)
        if remove_token:
            message = (
                "Conta desconectada e token local removido."
                if removed
                else "Conta desconectada. Nenhum token local encontrado."
            )
        else:
            message = "Conta desconectada."
        self.window.set_status(message, "offline")
        self.window.set_buttons_enabled(connect=True, search=False, rank=False)
        self.window.navigate_to_page(0)

    def search_sender(self) -> None:
        if self.gmail_service is None:
            self.window.set_status("Conecte ao Gmail antes de buscar.", "offline")
            return

        remetente = self.window.get_sender()
        if not remetente:
            self.window.set_status("Digite um remetente para buscar.", "idle")
            return

        self.window.set_status("Analisando e-mails do remetente...", "searching")
        self.ranking_mode = False
        self.window.show_loading(True)
        self.window.set_buttons_enabled(connect=False, search=False, rank=False)
        QApplication.processEvents()

        try:
            resultado = buscar_emails_por_remetente(
                self.gmail_service,
                remetente,
                self._update_search_progress,
            )
        except Exception as error:
            self.current_emails = []
            self.cleanable_message_ids = []
            self.protected_count = 0
            self.window.show_loading(False)
            self.window.set_status(f"Erro ao buscar e-mails: {error}", "error")
            self.window.set_buttons_enabled(
                connect=True,
                search=True,
                rank=True,
                next_sender=self._has_next_sender(),
            )
            return

        self.current_emails = resultado.emails
        self._apply_exceptions_and_render(remetente)
        self.window.show_loading(False)
        self.window.set_status(
            f"{len(self.cleanable_message_ids)} de {resultado.total} e-mail(s) podem ser limpos.",
            "done",
        )
        self.window.set_buttons_enabled(
            connect=True,
            search=True,
            rank=True,
            trash=bool(self.cleanable_message_ids),
            next_sender=bool(self.sender_ranking),
        )

    def find_sender_ranking(self) -> None:
        if self.gmail_service is None:
            self.window.set_status(
                "Conecte ao Gmail antes de buscar o ranking.", "offline"
            )
            return

        if not self.sender_ranking:
            self.window.set_status(
                "Carregando remetentes com mais e-mails...", "searching"
            )
            self.window.show_loading(True)
            self.window.set_buttons_enabled(connect=False, search=False, rank=False)
            QApplication.processEvents()

            try:
                self.sender_ranking = listar_remetentes_por_volume(
                    self.gmail_service,
                    self._update_sender_ranking_progress,
                )
            except Exception as error:
                self.sender_ranking = []
                self.current_sender_index = 0
                self.window.show_loading(False)
                self.window.set_status(f"Erro ao buscar ranking: {error}", "error")
                self.window.set_buttons_enabled(connect=True, search=True, rank=True)
                return
            self.window.show_loading(False)

        self.current_sender_index = 0
        self.current_emails = []
        self.cleanable_message_ids = []
        self.protected_count = 0
        self.ranking_mode = True

        if not self.sender_ranking:
            self.window.show_result_rows([])
            self.window.set_status("Nenhum remetente encontrado para ranquear.", "idle")
            self.window.set_buttons_enabled(connect=True, search=True, rank=True)
            return

        self._show_current_sender()
        self.window.set_buttons_enabled(
            connect=True,
            search=True,
            rank=True,
            next_sender=True,
        )

    def select_sender_from_ranking(self, row: int, _column: int) -> None:
        if not self.ranking_mode or row < 0 or row >= len(self.sender_ranking):
            return

        self.current_sender_index = row
        self.current_emails = []
        self.cleanable_message_ids = []
        self.protected_count = 0
        self._show_current_sender()
        self.window.set_buttons_enabled(
            connect=True,
            search=True,
            rank=True,
            next_sender=True,
        )

    def next_sender(self) -> None:
        if not self.sender_ranking:
            self.window.set_status("Nenhum ranking de remetentes carregado.", "idle")
            return

        if not self._has_next_sender():
            self.window.set_status("Voce chegou ao ultimo remetente da lista.", "idle")
            self.window.set_buttons_enabled(
                connect=True,
                search=True,
                rank=True,
                next_sender=False,
            )
            return

        self.current_sender_index += 1
        self.current_emails = []
        self.cleanable_message_ids = []
        self.protected_count = 0
        self.ranking_mode = True
        self._show_current_sender()
        self.window.set_buttons_enabled(
            connect=True,
            search=True,
            rank=True,
            next_sender=self._has_next_sender(),
        )

    def move_found_to_trash(self) -> None:
        if self.gmail_service is None:
            self.window.set_status("Conecte ao Gmail antes de mover emails.", "offline")
            return

        self._apply_exceptions_and_render(self.window.get_sender())
        if not self.cleanable_message_ids:
            self.window.set_status("Nenhum e-mail liberado pelas excecoes.", "idle")
            return

        if not self.window.confirm_move_to_trash(
            len(self.cleanable_message_ids),
            self.protected_count,
        ):
            self.window.set_status("Operacao cancelada.", "idle")
            return

        self.window.set_status(
            "Movendo e-mails selecionados para a lixeira...", "searching"
        )
        self.window.show_loading(True)
        self.window.set_buttons_enabled(
            connect=False,
            search=False,
            trash=False,
            rank=False,
        )
        QApplication.processEvents()

        moved_emails = [
            email
            for email in self.current_emails
            if email.message_id in set(self.cleanable_message_ids)
        ]

        try:
            moved_count = mover_emails_para_lixeira(
                self.gmail_service,
                self.cleanable_message_ids,
                self._update_trash_progress,
            )
            write_cleanup_log(
                account_email=self.account_email,
                sender_query=self.window.get_sender(),
                moved_emails=moved_emails,
                protected_count=self.protected_count,
            )
        except Exception as error:
            self.window.show_loading(False)
            self.window.set_status(f"Erro ao mover para a lixeira: {error}", "error")
            self.window.set_buttons_enabled(
                connect=True,
                search=True,
                trash=True,
                rank=True,
                next_sender=self._has_next_sender(),
            )
            return

        self.current_emails = [
            email
            for email in self.current_emails
            if email.message_id not in set(self.cleanable_message_ids)
        ]
        self.cleanable_message_ids = []
        self._apply_exceptions_and_render(self.window.get_sender())
        self.window.show_loading(False)
        self.window.set_status(
            f"Limpeza finalizada: {moved_count} e-mail(s) movido(s) para a lixeira.",
            "done",
        )
        self.window.set_buttons_enabled(
            connect=True,
            search=True,
            rank=True,
            trash=bool(self.cleanable_message_ids),
            next_sender=self._has_next_sender(),
        )

    def _apply_exceptions_and_render(self, remetente: str) -> None:
        settings = self.window.get_exception_settings()
        protections = apply_exception_rules(self.current_emails, settings)
        protection_by_id = {
            protection.message_id: protection for protection in protections
        }

        cleanable = []
        protected_rows = []
        for email in self.current_emails:
            protection = protection_by_id[email.message_id]
            reason = protection.reason

            if reason:
                protected_rows.append(_protected_row(email, reason))
            else:
                cleanable.append(email)

        self.cleanable_message_ids = [email.message_id for email in cleanable]
        self.protected_count = len(protected_rows)
        summary = _summary(
            self.total_messages,
            len(self.sender_ranking),
            self.current_emails,
            cleanable,
            self.protected_count,
        )
        rows = _result_rows(remetente, self.current_emails, cleanable, protected_rows)
        self.window.show_summary(summary)
        self.window.show_result_rows(rows)
        self.window.show_protected_rows(protected_rows)

    def _refresh_current_analysis(self) -> None:
        if not self.current_emails:
            return

        self._apply_exceptions_and_render(self.window.get_sender())
        self.window.set_buttons_enabled(
            connect=True,
            search=True,
            rank=True,
            trash=bool(self.cleanable_message_ids),
            next_sender=self._has_next_sender(),
        )

    def _connect_exception_controls(self) -> None:
        refresh = lambda *_: self._refresh_current_analysis()
        self.window.protect_attachments_check.toggled.connect(refresh)
        self.window.protect_recent_check.toggled.connect(refresh)
        self.window.protect_important_check.toggled.connect(refresh)
        self.window.recent_days_input.valueChanged.connect(refresh)
        self.window.protected_senders_input.textChanged.connect(refresh)
        self.window.protected_domains_input.textChanged.connect(refresh)
        self.window.subject_keywords_input.textChanged.connect(refresh)
        self.window.body_keywords_input.textChanged.connect(refresh)

    def _show_current_sender(self) -> None:
        current_sender = self.sender_ranking[self.current_sender_index]
        self.window.set_sender(current_sender.email)
        self.window.show_sender_ranking(
            self.sender_ranking,
            self.current_sender_index,
        )
        self.window.set_status(
            (
                f"Remetente {self.current_sender_index + 1} de "
                f"{len(self.sender_ranking)} selecionado para pre-visualizacao."
            ),
            "idle",
        )

    def _has_next_sender(self) -> bool:
        return self.current_sender_index < len(self.sender_ranking) - 1

    def _clear_state(self) -> None:
        self.gmail_service = None
        self.total_messages = 0
        self.sender_ranking = []
        self.current_sender_index = 0
        self.current_emails = []
        self.cleanable_message_ids = []
        self.protected_count = 0
        self.account_email = ""

    def _update_search_progress(self, current: int, total: int) -> None:
        if total == 0:
            self.window.set_status("Nenhum e-mail encontrado para ler.", "searching")
        elif current == 0:
            self.window.set_status(
                f"Preparando analise de {total} e-mail(s)...", "searching"
            )
        else:
            self.window.set_status(
                f"Analisando e-mail {current} de {total}...", "searching"
            )
        self.window.show_progress(current, total)
        QApplication.processEvents()

    def _update_sender_ranking_progress(self, current: int, total: int) -> None:
        if total == 0:
            self.window.set_status(
                "Nenhum e-mail encontrado para ranquear.", "searching"
            )
        elif current == 0:
            self.window.set_status(
                f"Preparando resumo de {total} e-mail(s)...", "searching"
            )
        else:
            self.window.set_status(
                f"Analisando remetente {current} de {total}...", "searching"
            )
        self.window.show_progress(current, total)
        QApplication.processEvents()

    def _update_trash_progress(self, current: int, total: int) -> None:
        if current == 0:
            self.window.set_status(
                f"Preparando limpeza de {total} e-mail(s)...", "searching"
            )
        else:
            self.window.set_status(
                f"Limpando e-mail {current} de {total}...", "searching"
            )
        self.window.show_progress(current, total)
        QApplication.processEvents()


def _summary(
    total_messages: int,
    unique_senders: int,
    all_emails: list[EmailAnalysis],
    cleanable: list[EmailAnalysis],
    protected_count: int,
) -> dict[str, object]:
    return {
        "total_messages": total_messages,
        "found": len(all_emails),
        "cleanable": len(cleanable),
        "protected": protected_count,
        "unique_senders": unique_senders,
        "estimated_space": _format_size(
            sum(email.size_estimate for email in cleanable)
        ),
    }


def _result_rows(
    remetente: str,
    all_emails: list[EmailAnalysis],
    cleanable: list[EmailAnalysis],
    protected_rows: list[dict[str, object]],
) -> list[dict[str, object]]:
    if not all_emails:
        return []

    protected_reason = _most_common_reason(protected_rows)
    protected_count = len(protected_rows)
    cleanable_count = len(cleanable)
    with_attachment = sum(1 for email in all_emails if email.has_attachment)
    status = "Seguro apagar"
    if protected_count and cleanable_count:
        status = (
            "Atencao: possui anexos" if with_attachment else "Selecionado para limpeza"
        )
    elif protected_count and not cleanable_count:
        status = "Protegido"
    elif cleanable_count:
        status = "Selecionado para limpeza"

    return [
        {
            "selected": bool(cleanable_count),
            "sender": remetente or all_emails[0].sender,
            "total": len(all_emails),
            "without_attachment": sum(
                1 for email in all_emails if not email.has_attachment
            ),
            "protected_count": protected_count,
            "estimated_space": _format_size(
                sum(email.size_estimate for email in cleanable)
            ),
            "status": status,
            "protection_reason": protected_reason,
            "action": "Selecionar | Proteger | Pre-visualizar | Limpar",
        }
    ]


def _protected_row(email: EmailAnalysis, reason: str) -> dict[str, object]:
    return {
        "sender": email.sender,
        "subject": email.subject,
        "reason": reason,
        "date": email.received_at.date().isoformat() if email.received_at else "-",
        "size": _format_size(email.size_estimate),
    }


def _most_common_reason(rows: list[dict[str, object]]) -> str:
    if not rows:
        return ""

    counts = Counter(str(row["reason"]) for row in rows)
    return counts.most_common(1)[0][0]


def _format_size(size_bytes: int) -> str:
    if size_bytes >= 1024 * 1024 * 1024:
        return f"{size_bytes / (1024 * 1024 * 1024):.2f} GB"
    if size_bytes >= 1024 * 1024:
        return f"{size_bytes / (1024 * 1024):.1f} MB"
    return f"{size_bytes / 1024:.1f} KB" if size_bytes else "0 MB"
