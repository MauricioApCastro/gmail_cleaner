from __future__ import annotations

from pathlib import Path

from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QColor
from PyQt6.QtWidgets import (
    QCheckBox,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMessageBox,
    QProgressBar,
    QPushButton,
    QSpinBox,
    QStackedWidget,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from src.services.exception_rules import ExceptionSettings
from src.services.gmail_actions import RemetenteVolume


class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()

        self.setWindowTitle("Gmail Cleaner")
        self.setMinimumSize(1180, 760)

        self.page_titles = [
            ("Dashboard", "Busca manual por remetente e resumo da limpeza."),
            ("Remetentes", "Ranking e pre-visualizacao por remetente."),
            ("Protegidos", "E-mails preservados pelas regras de excecao."),
            ("Exceções", "Regras que impedem a limpeza automatica."),
        ]
        self.nav_buttons: list[QPushButton] = []
        self.current_theme = "light"

        self.connect_button = QPushButton("Conectar Gmail")
        self.connect_button.setObjectName("primaryButton")

        self.theme_button = QPushButton("Tema escuro")
        self.theme_button.setObjectName("themeButton")
        self.theme_button.clicked.connect(self.toggle_theme)

        self.search_button = QPushButton("Buscar")
        self.search_button.setObjectName("primaryButton")
        self.search_button.setEnabled(False)

        self.rank_button = QPushButton("Encontrar ranking")
        self.rank_button.setObjectName("primaryButton")
        self.rank_button.setEnabled(False)

        self.next_button = QPushButton("Pre-visualizar limpeza")
        self.next_button.setObjectName("primaryButton")
        self.next_button.setEnabled(False)

        self.trash_button = QPushButton("Limpar selecionados")
        self.trash_button.setObjectName("dangerButton")
        self.trash_button.setEnabled(False)

        self.sender_input = QLineEdit()
        self.sender_input.setPlaceholderText("Digite o remetente")
        self.sender_input.textChanged.connect(self.sender_input.setToolTip)

        self.status_dot = QLabel()
        self.status_dot.setObjectName("statusDot")
        self.status_label = QLabel("Desconectado")
        self.status_label.setObjectName("statusText")

        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        self.progress_bar.setVisible(False)
        self.progress_bar.setTextVisible(False)

        self.total_messages_card = _StatCard("Total de mensagens", "0")
        self.found_card = _StatCard("E-mails encontrados", "0")
        self.safe_card = _StatCard("Sem anexo", "0")
        self.protected_card = _StatCard("Protegidos", "0")
        self.unique_senders_card = _StatCard("Remetentes unicos", "0")
        self.estimated_space_card = _StatCard("Espaco liberavel", "0 MB")

        self.result_table = QTableWidget(0, 9)
        self.result_table.setHorizontalHeaderLabels(
            [
                "Selecionar",
                "Remetente",
                "Total",
                "Sem anexo",
                "Com anexo / Protegidos",
                "Espaco estimado",
                "Status",
                "Motivo da protecao",
                "Acao",
            ]
        )
        self._prepare_table(self.result_table, min_height=360)

        self.protected_table = QTableWidget(0, 5)
        self.protected_table.setHorizontalHeaderLabels(
            ["Remetente", "Assunto", "Motivo", "Data", "Tamanho"]
        )
        self._prepare_table(self.protected_table, min_height=420)

        self.protect_attachments_check = QCheckBox("E-mails com anexo")
        self.protect_attachments_check.setChecked(True)
        self.protect_recent_check = QCheckBox("Data recente")
        self.protect_recent_check.setChecked(True)
        self.protect_important_check = QCheckBox("Importante/estrela")
        self.protect_important_check.setChecked(True)
        self.recent_days_input = QSpinBox()
        self.recent_days_input.setRange(0, 3650)
        self.recent_days_input.setValue(30)
        self.protected_senders_input = QLineEdit()
        self.protected_senders_input.setPlaceholderText(
            "remetente@dominio.com, outro@dominio.com"
        )
        self.protected_domains_input = QLineEdit()
        self.protected_domains_input.setPlaceholderText("@empresa.com, @cliente.com")
        self.subject_keywords_input = QLineEdit()
        self.subject_keywords_input.setPlaceholderText("contrato, boleto, nota fiscal")
        self.body_keywords_input = QLineEdit()
        self.body_keywords_input.setPlaceholderText("palavras no corpo do e-mail")

        self._build_layout()
        self._load_stylesheet()
        self.set_status("Desconectado", "offline")
        self.reset_result()

    def _build_layout(self) -> None:
        root = QHBoxLayout()
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)
        root.addWidget(self._build_sidebar())
        root.addWidget(self._build_content(), 1)

        container = QWidget()
        container.setObjectName("appRoot")
        container.setLayout(root)
        self.setCentralWidget(container)

    def _build_sidebar(self) -> QFrame:
        sidebar = QFrame()
        sidebar.setObjectName("sidebar")
        sidebar.setFixedWidth(238)

        logo = QLabel("Gmail Cleaner")
        logo.setObjectName("logo")

        nav_layout = QVBoxLayout()
        nav_layout.setSpacing(8)
        for index, item in enumerate(["Dashboard", "Remetentes", "Protegidos", "Exceções"]):
            button = QPushButton(item)
            button.setObjectName("navButtonActive" if index == 0 else "navButton")
            button.clicked.connect(
                lambda _checked=False, page=index: self.navigate_to_page(page)
            )
            self.nav_buttons.append(button)
            nav_layout.addWidget(button)

        layout = QVBoxLayout()
        layout.setContentsMargins(22, 24, 22, 24)
        layout.setSpacing(18)
        layout.addWidget(logo)
        layout.addSpacing(12)
        layout.addLayout(nav_layout)
        layout.addStretch()
        layout.addWidget(self.theme_button)
        layout.addWidget(self.connect_button)
        sidebar.setLayout(layout)
        return sidebar

    def _build_content(self) -> QFrame:
        content = QFrame()
        content.setObjectName("content")

        self.page_title_label = QLabel(self.page_titles[0][0])
        self.page_title_label.setObjectName("pageTitle")
        self.page_subtitle_label = QLabel(self.page_titles[0][1])
        self.page_subtitle_label.setObjectName("pageSubtitle")

        status_wrap = QFrame()
        status_wrap.setObjectName("statusPill")
        status_layout = QHBoxLayout()
        status_layout.setContentsMargins(14, 8, 14, 8)
        status_layout.setSpacing(8)
        status_layout.addWidget(self.status_dot)
        status_layout.addWidget(self.status_label)
        status_wrap.setLayout(status_layout)

        header_layout = QHBoxLayout()
        header_layout.addWidget(self.page_title_label)
        header_layout.addStretch()
        header_layout.addWidget(status_wrap)

        self.pages = QStackedWidget()
        self.pages.addWidget(self._build_dashboard_page())
        self.pages.addWidget(self._build_senders_page())
        self.pages.addWidget(self._build_protected_page())
        self.pages.addWidget(self._build_exceptions_page())

        layout = QVBoxLayout()
        layout.setContentsMargins(30, 26, 30, 30)
        layout.setSpacing(16)
        layout.addLayout(header_layout)
        layout.addWidget(self.page_subtitle_label)
        layout.addWidget(self.pages, 1)
        content.setLayout(layout)
        return content

    def _build_dashboard_page(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(16)
        layout.addWidget(self._build_search_panel())
        layout.addLayout(self._build_cards_layout())
        layout.addStretch()
        page.setLayout(layout)
        return page

    def _build_senders_page(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(16)
        layout.addWidget(self._build_table_panel(), 1)
        page.setLayout(layout)
        return page

    def _build_protected_page(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(16)
        layout.addWidget(self._build_protected_panel(), 1)
        page.setLayout(layout)
        return page

    def _build_exceptions_page(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(16)
        layout.addWidget(self._build_exceptions_panel())
        layout.addStretch()
        page.setLayout(layout)
        return page

    def _build_search_panel(self) -> QFrame:
        panel = QFrame()
        panel.setObjectName("panel")
        layout = QGridLayout()
        layout.setContentsMargins(22, 20, 22, 20)
        layout.setHorizontalSpacing(12)
        layout.setVerticalSpacing(12)

        field_label = QLabel("Remetente")
        field_label.setObjectName("fieldLabel")
        layout.addWidget(field_label, 0, 0, 1, 4)
        layout.addWidget(self.sender_input, 1, 0, 1, 4)
        layout.addWidget(self.search_button, 2, 0)
        layout.addWidget(self.rank_button, 2, 1)
        layout.addWidget(self.next_button, 2, 2)
        layout.addWidget(self.trash_button, 2, 3)
        layout.addWidget(self.progress_bar, 3, 0, 1, 4)
        layout.setColumnStretch(0, 1)
        panel.setLayout(layout)
        return panel

    def _build_cards_layout(self) -> QGridLayout:
        layout = QGridLayout()
        layout.setHorizontalSpacing(14)
        layout.setVerticalSpacing(14)
        cards = [
            self.total_messages_card,
            self.found_card,
            self.safe_card,
            self.protected_card,
            self.unique_senders_card,
            self.estimated_space_card,
        ]
        for index, card in enumerate(cards):
            layout.addWidget(card, index // 3, index % 3)
        return layout

    def _build_table_panel(self) -> QFrame:
        panel = QFrame()
        panel.setObjectName("panel")
        layout = QVBoxLayout()
        layout.setContentsMargins(22, 20, 22, 22)
        title = QLabel("Remetentes por quantidade")
        title.setObjectName("sectionTitle")
        layout.addWidget(title)
        layout.addWidget(self.result_table, 1)
        panel.setLayout(layout)
        return panel

    def _build_exceptions_panel(self) -> QFrame:
        panel = QFrame()
        panel.setObjectName("panel")
        layout = QGridLayout()
        layout.setContentsMargins(22, 20, 22, 22)
        layout.setHorizontalSpacing(12)
        layout.setVerticalSpacing(10)

        title = QLabel("Exceções / Proteções")
        title.setObjectName("sectionTitle")
        layout.addWidget(title, 0, 0, 1, 4)
        layout.addWidget(self.protect_attachments_check, 1, 0)
        layout.addWidget(self.protect_recent_check, 1, 1)
        layout.addWidget(_form_label("Ultimos dias"), 1, 2)
        layout.addWidget(self.recent_days_input, 1, 3)
        layout.addWidget(self.protect_important_check, 2, 0)
        layout.addWidget(_form_label("Remetentes protegidos"), 3, 0)
        layout.addWidget(self.protected_senders_input, 3, 1, 1, 3)
        layout.addWidget(_form_label("Dominios protegidos"), 4, 0)
        layout.addWidget(self.protected_domains_input, 4, 1, 1, 3)
        layout.addWidget(_form_label("Assunto contem"), 5, 0)
        layout.addWidget(self.subject_keywords_input, 5, 1, 1, 3)
        layout.addWidget(_form_label("Corpo contem"), 6, 0)
        layout.addWidget(self.body_keywords_input, 6, 1, 1, 3)
        panel.setLayout(layout)
        return panel

    def _build_protected_panel(self) -> QFrame:
        panel = QFrame()
        panel.setObjectName("panel")
        layout = QVBoxLayout()
        layout.setContentsMargins(22, 20, 22, 22)
        title = QLabel("Protegidos")
        title.setObjectName("sectionTitle")
        layout.addWidget(title)
        layout.addWidget(self.protected_table, 1)
        panel.setLayout(layout)
        return panel

    def navigate_to_page(self, page: int) -> None:
        self.pages.setCurrentIndex(page)
        title, subtitle = self.page_titles[page]
        self.page_title_label.setText(title)
        self.page_subtitle_label.setText(subtitle)
        for index, button in enumerate(self.nav_buttons):
            button.setObjectName("navButtonActive" if index == page else "navButton")
            button.style().unpolish(button)
            button.style().polish(button)

    def _prepare_table(self, table: QTableWidget, min_height: int) -> None:
        table.verticalHeader().setVisible(False)
        table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        table.setAlternatingRowColors(True)
        table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        table.horizontalHeader().setSectionResizeMode(
            0,
            QHeaderView.ResizeMode.ResizeToContents,
        )
        table.setMinimumHeight(min_height)

    def _load_stylesheet(self) -> None:
        style_path = (
            Path(__file__).resolve().parent
            / "styles"
            / f"{self.current_theme}_theme.qss"
        )
        self.setStyleSheet(style_path.read_text(encoding="utf-8"))

    def toggle_theme(self) -> None:
        self.current_theme = "dark" if self.current_theme == "light" else "light"
        self.theme_button.setText(
            "Tema claro" if self.current_theme == "dark" else "Tema escuro"
        )
        self._load_stylesheet()

    def set_status(self, message: str, state: str = "idle") -> None:
        self.status_label.setText(message)
        self.status_dot.setProperty("state", state)
        self.status_dot.style().unpolish(self.status_dot)
        self.status_dot.style().polish(self.status_dot)

    def set_buttons_enabled(
        self,
        connect: bool,
        search: bool,
        trash: bool = False,
        rank: bool = False,
        next_sender: bool = False,
    ) -> None:
        self.connect_button.setEnabled(connect)
        self.search_button.setEnabled(search)
        self.rank_button.setEnabled(rank)
        self.trash_button.setEnabled(trash)
        self.next_button.setEnabled(next_sender)

    def set_connected_state(self, connected: bool) -> None:
        if connected:
            self.connect_button.setText("Desconectar conta")
            self.connect_button.setObjectName("dangerButton")
        else:
            self.connect_button.setText("Conectar Gmail")
            self.connect_button.setObjectName("primaryButton")
        self.connect_button.style().unpolish(self.connect_button)
        self.connect_button.style().polish(self.connect_button)

    def get_sender(self) -> str:
        return self.sender_input.text().strip()

    def set_sender(self, remetente: str) -> None:
        self.sender_input.setText(remetente)

    def get_exception_settings(self) -> ExceptionSettings:
        return ExceptionSettings(
            protected_senders=_split_values(self.protected_senders_input.text()),
            protected_domains=_split_values(self.protected_domains_input.text()),
            subject_keywords=_split_values(self.subject_keywords_input.text()),
            body_keywords=_split_values(self.body_keywords_input.text()),
            protect_attachments=self.protect_attachments_check.isChecked(),
            protect_recent_days=(
                self.recent_days_input.value()
                if self.protect_recent_check.isChecked()
                else 0
            ),
            protect_starred_or_important=self.protect_important_check.isChecked(),
        )

    def show_loading(self, active: bool) -> None:
        self.progress_bar.setVisible(active)
        if active:
            self.progress_bar.setRange(0, 0)
        else:
            self.progress_bar.setRange(0, 100)
            self.progress_bar.setValue(100)
            QTimer.singleShot(700, lambda: self.progress_bar.setVisible(False))

    def show_progress(self, current: int, total: int) -> None:
        self.progress_bar.setVisible(True)
        self.progress_bar.setRange(0, max(total, 1))
        self.progress_bar.setValue(min(current, total))

    def show_summary(self, summary: dict[str, object]) -> None:
        self.total_messages_card.set_value(str(summary.get("total_messages", 0)))
        self.found_card.set_value(str(summary.get("found", 0)))
        self.safe_card.set_value(str(summary.get("cleanable", 0)))
        self.protected_card.set_value(str(summary.get("protected", 0)))
        self.unique_senders_card.set_value(str(summary.get("unique_senders", 0)))
        self.estimated_space_card.set_value(str(summary.get("estimated_space", "0 MB")))

    def show_result_rows(self, rows: list[dict[str, object]]) -> None:
        self.result_table.setRowCount(len(rows))
        for row_index, row in enumerate(rows):
            selected = bool(row.get("selected", False))
            status = str(row.get("status", ""))
            self.result_table.setItem(row_index, 0, _checkbox_item(selected))
            self.result_table.setItem(row_index, 1, QTableWidgetItem(str(row["sender"])))
            self.result_table.setItem(row_index, 2, QTableWidgetItem(str(row["total"])))
            self.result_table.setItem(
                row_index,
                3,
                QTableWidgetItem(str(row["without_attachment"])),
            )
            self.result_table.setItem(
                row_index,
                4,
                QTableWidgetItem(str(row["protected_count"])),
            )
            self.result_table.setItem(
                row_index,
                5,
                QTableWidgetItem(str(row["estimated_space"])),
            )
            self.result_table.setItem(row_index, 6, _status_item(status, self.current_theme))
            self.result_table.setItem(
                row_index,
                7,
                QTableWidgetItem(str(row["protection_reason"])),
            )
            self.result_table.setItem(row_index, 8, QTableWidgetItem(str(row["action"])))
            self.result_table.setRowHeight(row_index, 42)

    def show_protected_rows(self, rows: list[dict[str, object]]) -> None:
        self.protected_table.setRowCount(len(rows))
        for row_index, row in enumerate(rows):
            self.protected_table.setItem(row_index, 0, QTableWidgetItem(str(row["sender"])))
            self.protected_table.setItem(row_index, 1, QTableWidgetItem(str(row["subject"])))
            self.protected_table.setItem(row_index, 2, QTableWidgetItem(str(row["reason"])))
            self.protected_table.setItem(row_index, 3, QTableWidgetItem(str(row["date"])))
            self.protected_table.setItem(row_index, 4, QTableWidgetItem(str(row["size"])))
            self.protected_table.setRowHeight(row_index, 38)

    def show_sender_ranking(
        self,
        remetentes: list[RemetenteVolume],
        current_index: int = 0,
        limit: int = 50,
    ) -> None:
        start_index = current_index if current_index >= limit else 0
        rows = []
        for index, sender in enumerate(remetentes[start_index : start_index + limit]):
            sender_index = start_index + index
            rows.append(
                {
                    "selected": sender_index == current_index,
                    "sender": sender.remetente,
                    "total": sender.total,
                    "without_attachment": "-",
                    "protected_count": "-",
                    "estimated_space": "-",
                    "status": (
                        "Selecionado para limpeza"
                        if sender_index == current_index
                        else "Seguro apagar"
                    ),
                    "protection_reason": "",
                    "action": "Selecionar | Proteger | Pre-visualizar | Limpar",
                }
            )
        self.show_result_rows(rows)
        self.navigate_to_page(1)

    def reset_result(self) -> None:
        self.show_summary(
            {
                "total_messages": 0,
                "found": 0,
                "cleanable": 0,
                "protected": 0,
                "unique_senders": 0,
                "estimated_space": "0 MB",
            }
        )
        self.show_result_rows([])
        self.show_protected_rows([])

    def confirm_move_to_trash(self, quantidade: int, protegidos: int) -> bool:
        resposta = QMessageBox.question(
            self,
            "Confirmar limpeza",
            (
                f"{quantidade} e-mail(s) serao movidos para a lixeira.\n"
                f"{protegidos} e-mail(s) foram protegidos por regras de excecao.\n"
                "Deseja continuar?"
            ),
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        return resposta == QMessageBox.StandardButton.Yes


class _StatCard(QFrame):
    def __init__(self, title: str, value: str) -> None:
        super().__init__()
        self.setObjectName("statCard")

        self.value_label = QLabel(value)
        self.value_label.setObjectName("statValue")
        title_label = QLabel(title)
        title_label.setObjectName("statTitle")
        accent = QFrame()
        accent.setObjectName("statAccent")

        layout = QVBoxLayout()
        layout.setContentsMargins(20, 16, 20, 16)
        layout.setSpacing(8)
        layout.addWidget(accent)
        layout.addWidget(self.value_label)
        layout.addWidget(title_label)
        self.setLayout(layout)

    def set_value(self, value: str) -> None:
        self.value_label.setText(value)


def _checkbox_item(checked: bool) -> QTableWidgetItem:
    item = QTableWidgetItem()
    item.setFlags(
        Qt.ItemFlag.ItemIsEnabled
        | Qt.ItemFlag.ItemIsUserCheckable
        | Qt.ItemFlag.ItemIsSelectable
    )
    item.setCheckState(Qt.CheckState.Checked if checked else Qt.CheckState.Unchecked)
    return item


def _status_item(status: str, theme: str) -> QTableWidgetItem:
    item = QTableWidgetItem(status)
    if theme == "dark":
        colors = {
            "Seguro apagar": QColor("#1e3a2b"),
            "Selecionado para limpeza": QColor("#263850"),
            "Atencao: possui anexos": QColor("#4a3514"),
            "Protegido": QColor("#3c4043"),
        }
        item.setForeground(QColor("#f1f3f4"))
    else:
        colors = {
            "Seguro apagar": QColor("#e6f4ea"),
            "Selecionado para limpeza": QColor("#e8f0fe"),
            "Atencao: possui anexos": QColor("#fef7e0"),
            "Protegido": QColor("#f1f3f4"),
        }
        item.setForeground(QColor("#202124"))
    item.setBackground(colors.get(status, QColor("#2b2c2f" if theme == "dark" else "#ffffff")))
    return item


def _form_label(text: str) -> QLabel:
    label = QLabel(text)
    label.setObjectName("fieldLabel")
    return label


def _split_values(value: str) -> set[str]:
    return {
        part.strip().lower()
        for part in value.replace("\n", ",").split(",")
        if part.strip()
    }
