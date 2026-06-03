from __future__ import annotations

from dataclasses import replace

from PyQt6.QtCore import QObject
from PyQt6.QtWidgets import QApplication

from src.auth.oauth import get_gmail_service
from src.auth.token_manager import remove_local_token
from src.services.history_service import write_cleanup_log
from src.services.exception_rules import apply_exception_rules
from src.services.cleanup_service import (
    EmailAnalysis,
    buscar_emails_por_remetente,
    definir_email_importante,
    listar_remetentes_por_volume,
    mover_emails_para_lixeira,
)
from src.services.gmail_service import (
    pegar_email_logado,
    quantidade_total,
)


class AnalysisCancelled(Exception):
    pass


class RankingCancelled(Exception):
    pass


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
        self.analysis_running = False
        self.cancel_analysis_requested = False
        self.ranking_running = False
        self.cancel_ranking_requested = False

        self.window.connect_button.clicked.connect(self.toggle_gmail_connection)
        self.window.search_button.clicked.connect(self.search_sender)
        self.window.rank_button.clicked.connect(self.find_sender_ranking)
        self.window.next_button.clicked.connect(self.next_sender)
        self.window.trash_button.clicked.connect(self.move_found_to_trash)
        self.window.result_table.cellClicked.connect(self.select_sender_from_ranking)
        self.window.email_table.cellDoubleClicked.connect(self.toggle_email_importance)
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
            "Pronto para analisar remetentes.",
            "connected",
        )
        self.window.set_connected_state(True)
        self.window.set_account_email(email_address)
        self.window.set_buttons_enabled(connect=True, search=True, rank=True)

    def disconnect_gmail(self, remove_token: bool = False) -> None:
        removed = remove_local_token() if remove_token else False
        self._clear_state()
        self.window.show_loading(False)
        self.window.reset_result()
        self.window.set_sender("")
        self.window.set_connected_state(False)
        self.window.set_account_email("")
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
        if self.analysis_running:
            self.cancel_analysis_requested = True
            self.window.set_search_running(True, stopping=True)
            self.window.set_status("Cancelando analise...", "idle")
            return

        if self.gmail_service is None:
            self.window.set_status("Conecte ao Gmail antes de buscar.", "offline")
            return

        remetente = self.window.get_sender()
        if not remetente:
            self.window.set_status("Digite um remetente para buscar.", "idle")
            return

        self.window.set_status("Analisando e-mails do remetente...", "searching")
        self.ranking_mode = False
        self.analysis_running = True
        self.cancel_analysis_requested = False
        self.window.show_loading(True)
        self.window.set_buttons_enabled(connect=False, search=True, rank=False)
        self.window.set_search_running(True)
        QApplication.processEvents()

        try:
            resultado = buscar_emails_por_remetente(
                self.gmail_service,
                remetente,
                self._update_search_progress,
            )
        except AnalysisCancelled:
            self.window.show_loading(False)
            self.window.set_search_running(False)
            self.window.set_status("Analise cancelada.", "idle")
            self.window.set_buttons_enabled(
                connect=True,
                search=True,
                rank=True,
                trash=bool(self.cleanable_message_ids),
                next_sender=self._has_next_sender(),
            )
            return
        except Exception as error:
            self.current_emails = []
            self.cleanable_message_ids = []
            self.protected_count = 0
            self.window.show_loading(False)
            self.window.set_search_running(False)
            self.window.set_status(f"Erro ao buscar e-mails: {error}", "error")
            self.window.set_buttons_enabled(
                connect=True,
                search=True,
                rank=True,
                next_sender=self._has_next_sender(),
            )
            return
        finally:
            self.analysis_running = False
            self.cancel_analysis_requested = False

        self.current_emails = resultado.emails
        self._apply_exceptions_and_render(remetente)
        self.window.show_loading(False)
        self.window.set_search_running(False)
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
        if self.ranking_running:
            self.cancel_ranking_requested = True
            self.window.set_ranking_running(True, stopping=True)
            self.window.set_status("Cancelando ranking...", "idle")
            return

        if self.gmail_service is None:
            self.window.set_status(
                "Conecte ao Gmail antes de buscar o ranking.", "offline"
            )
            return

        self.window.set_sender("")
        self.current_emails = []
        self.cleanable_message_ids = []
        self.protected_count = 0
        self.ranking_mode = False
        self.window.show_result_rows([])
        self.window.show_email_rows([])
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

        if not self.sender_ranking:
            self.window.set_status(
                "Carregando remetentes com mais e-mails...", "searching"
            )
            self.ranking_running = True
            self.cancel_ranking_requested = False
            self.window.show_loading(True)
            self.window.set_buttons_enabled(connect=False, search=False, rank=True)
            self.window.set_ranking_running(True)
            QApplication.processEvents()

            try:
                self.sender_ranking = listar_remetentes_por_volume(
                    self.gmail_service,
                    self._update_sender_ranking_progress,
                )
            except RankingCancelled:
                self.sender_ranking = []
                self.current_sender_index = 0
                self.window.show_loading(False)
                self.window.set_ranking_running(False)
                self.window.set_status("Ranking cancelado.", "idle")
                self.window.set_buttons_enabled(connect=True, search=True, rank=True)
                return
            except Exception as error:
                self.sender_ranking = []
                self.current_sender_index = 0
                self.window.show_loading(False)
                self.window.set_ranking_running(False)
                self.window.set_status(f"Erro ao buscar ranking: {error}", "error")
                self.window.set_buttons_enabled(connect=True, search=True, rank=True)
                return
            finally:
                self.ranking_running = False
                self.cancel_ranking_requested = False
            self.window.show_loading(False)
            self.window.set_ranking_running(False)

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
        
        # Atualizar o total de emails após a limpeza
        self.total_messages -= moved_count
        
        if self.ranking_mode:
            self._remove_current_sender_from_ranking()
        else:
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

    def toggle_email_importance(self, row: int, _column: int) -> None:
        if self.gmail_service is None:
            self.window.set_status("Conecte ao Gmail antes de alterar e-mails.", "offline")
            return

        message_id = self.window.get_visible_email_message_id(row)
        if not message_id:
            return

        email = self._find_current_email(message_id)
        if email is None:
            return

        labels = {label.upper() for label in email.label_ids}
        should_mark_important = "IMPORTANT" not in labels
        action = "Marcando" if should_mark_important else "Removendo importancia de"
        self.window.set_status(f"{action} e-mail...", "searching")
        QApplication.processEvents()

        try:
            definir_email_importante(
                self.gmail_service,
                message_id,
                should_mark_important,
            )
        except Exception as error:
            self.window.set_status(f"Erro ao alterar importancia: {error}", "error")
            return

        self._update_current_email_labels(message_id, should_mark_important)
        self.window.show_all_email_statuses()
        self._apply_exceptions_and_render(self.window.get_sender())
        self.window.set_buttons_enabled(
            connect=True,
            search=True,
            rank=True,
            trash=bool(self.cleanable_message_ids),
            next_sender=self._has_next_sender(),
        )
        status = "marcado como importante" if should_mark_important else "liberado da importancia"
        self.window.set_status(f"E-mail {status}.", "done")

    def _remove_current_sender_from_ranking(self) -> None:
        if not self.sender_ranking:
            self.window.show_result_rows([])
            return

        del self.sender_ranking[self.current_sender_index]
        self.current_emails = []
        self.cleanable_message_ids = []
        self.protected_count = 0

        if not self.sender_ranking:
            self.current_sender_index = 0
            self.ranking_mode = False
            self.window.set_sender("")
            self.window.show_result_rows([])
            self.window.show_email_rows([])
            return

        if self.current_sender_index >= len(self.sender_ranking):
            self.current_sender_index = len(self.sender_ranking) - 1

        self._show_current_sender()

    def _find_current_email(self, message_id: str) -> EmailAnalysis | None:
        return next(
            (email for email in self.current_emails if email.message_id == message_id),
            None,
        )

    def _update_current_email_labels(self, message_id: str, important: bool) -> None:
        updated_emails = []
        for email in self.current_emails:
            if email.message_id != message_id:
                updated_emails.append(email)
                continue

            labels = list(email.label_ids)
            has_important = any(label.upper() == "IMPORTANT" for label in labels)
            if important and not has_important:
                labels.append("IMPORTANT")
            elif not important:
                labels = [label for label in labels if label.upper() != "IMPORTANT"]
            updated_emails.append(replace(email, label_ids=labels))

        self.current_emails = updated_emails

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
        email_rows = _email_rows(self.current_emails, protection_by_id)
        self.window.show_summary(summary)
        self.window.show_result_rows(rows)
        self.window.show_email_rows(email_rows)

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
        self.analysis_running = False
        self.cancel_analysis_requested = False
        self.ranking_running = False
        self.cancel_ranking_requested = False

    def _update_search_progress(self, current: int, total: int) -> None:
        if self.cancel_analysis_requested:
            raise AnalysisCancelled

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
        if self.cancel_analysis_requested:
            raise AnalysisCancelled

    def _update_sender_ranking_progress(self, current: int, total: int) -> None:
        if self.cancel_ranking_requested:
            raise RankingCancelled

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
        if self.cancel_ranking_requested:
            raise RankingCancelled

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
            "cleanable_count": cleanable_count,
            "protected_count": protected_count,
            "estimated_space": _format_size(
                sum(email.size_estimate for email in cleanable)
            ),
            "status": status,
        }
    ]


def _protected_row(email: EmailAnalysis, reason: str) -> dict[str, object]:
    return {
        "message_id": email.message_id,
        "sender": email.sender,
        "subject": email.subject,
        "reason": reason,
        "date": email.received_at.date().isoformat() if email.received_at else "-",
        "size": _format_size(email.size_estimate),
    }


def _email_rows(emails: list[EmailAnalysis], protection_by_id: dict[str, object]) -> list[dict[str, object]]:
    rows = []
    for email in emails:
        protection = protection_by_id[email.message_id]
        rows.append(
            _protected_row(
                email,
                _email_status(email, protection.reason),
            )
        )
    return rows


def _email_status(email: EmailAnalysis, protection_reason: str) -> str:
    labels = {label.upper() for label in email.label_ids}
    if "IMPORTANT" in labels or "STARRED" in labels:
        return "Marcado como importante/estrela"
    return protection_reason if protection_reason else "Liberado para limpeza"


def _format_size(size_bytes: int) -> str:
    if size_bytes >= 1024 * 1024 * 1024:
        return f"{size_bytes / (1024 * 1024 * 1024):.2f} GB"
    if size_bytes >= 1024 * 1024:
        return f"{size_bytes / (1024 * 1024):.1f} MB"
    return f"{size_bytes / 1024:.1f} KB" if size_bytes else "0 MB"
