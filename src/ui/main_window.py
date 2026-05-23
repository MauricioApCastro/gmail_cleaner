from __future__ import annotations

from PyQt6.QtCore import QSettings, Qt, QTimer, pyqtSignal
from PyQt6.QtGui import QCloseEvent, QColor, QIcon, QPixmap
from PyQt6.QtWidgets import (
    QApplication,
    QCheckBox,
    QComboBox,
    QDialog,
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
    QSizePolicy,
    QSpinBox,
    QStackedWidget,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from src.config.settings import ICON_FILE, LOGO_FILE, THEMES_DIR
from src.services.cleanup_service import RemetenteVolume
from src.services.exception_rules import ExceptionSettings

MIN_WINDOW_WIDTH = 1200
MIN_WINDOW_HEIGHT = 700
FIRST_RUN_SCREEN_RATIO = 0.88


class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()

        self.setWindowTitle("Gmail Cleaner")
        if ICON_FILE.exists():
            self.setWindowIcon(QIcon(str(ICON_FILE)))
        self.setMinimumSize(MIN_WINDOW_WIDTH, MIN_WINDOW_HEIGHT)

        self.current_theme = "light"
        self.nav_labels = [
            "Análise",
            "E-mails",
            "Exceções",
            "Contas",
            "Suporte",
        ]

        self._create_shared_widgets()
        self._build_layout()
        self._load_stylesheet()
        self._restore_window_placement()
        self.set_status("Não conectado", "offline")
        self.set_connected_state(False)
        self.reset_result()

    def closeEvent(self, event: QCloseEvent) -> None:
        self._save_window_placement()
        super().closeEvent(event)

    def _create_shared_widgets(self) -> None:
        self.connect_button = QPushButton("Conectar Gmail")
        self.connect_button.setObjectName("primaryButton")

        self.search_button = QPushButton("🔍  Analisar")
        self.search_button.setObjectName("heroButton")
        self.search_button.setEnabled(False)

        self.rank_button = QPushButton("Ranking por volume")
        self.rank_button.setObjectName("secondaryButton")
        self.rank_button.setEnabled(False)

        self.next_button = QPushButton("Próximo remetente")
        self.next_button.setObjectName("secondaryButton")
        self.next_button.setEnabled(False)
        self.next_button.setVisible(False)

        self.trash_button = QPushButton("🗑 Limpar selecionados")
        self.trash_button.setObjectName("dangerButton")
        self.trash_button.setEnabled(False)

        self.sender_input = QLineEdit()
        self.sender_input.setPlaceholderText("Digite o remetente para analisar")
        self.sender_input.textChanged.connect(self.sender_input.setToolTip)

        self.status_dot = QLabel()
        self.status_dot.setObjectName("statusDot")
        self.status_label = QLabel("Não conectado")
        self.status_label.setObjectName("footerText")
        self.status_hint_label = QLabel("Conecte sua conta para começar.")
        self.status_hint_label.setObjectName("footerHintText")
        self.account_label = QLabel("Nenhuma conta conectada")
        self.account_label.setObjectName("accountBadge")
        self.account_label.setProperty("state", "disconnected")
        self.account_page_label = QLabel("Nenhuma conta conectada")
        self.account_page_label.setObjectName("accountPanelBadge")
        self.account_page_label.setProperty("state", "disconnected")

        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        self.progress_bar.setVisible(False)
        self.progress_bar.setTextVisible(False)

        self.total_messages_card = SummaryMetric("✉", "0", "Total de emails", "blue")
        self.safe_card = SummaryMetric("✉", "0", "Podem ser removidos", "green")
        self.estimated_space_card = SummaryMetric(
            "▱", "0 B", "Espaço recuperável", "orange"
        )
        self.protected_card = SummaryMetric("♢", "0", "Protegidos", "purple")

        self.found_card = SummaryMetric("✉", "0", "E-mails encontrados", "blue")
        self.unique_senders_card = SummaryMetric("◎", "0", "Remetentes únicos", "blue")

        self.result_table = QTableWidget(0, 7)
        self.result_table.setHorizontalHeaderLabels(
            [
                "Selecionar",
                "Remetente",
                "Total",
                "Pode limpar",
                "Protegidos",
                "Espaço estimado",
                "Status",
            ]
        )
        self._prepare_table(self.result_table, min_height=350)

        self.email_table = QTableWidget(0, 5)
        self.email_table.setHorizontalHeaderLabels(
            ["Remetente", "Assunto", "Status", "Data", "Tamanho"]
        )
        self._prepare_table(self.email_table, min_height=360)
        self._prepare_email_table()
        self.email_rows: list[dict[str, object]] = []
        self.visible_email_rows: list[dict[str, object]] = []
        self.email_reason_filter = QComboBox()
        self.email_reason_filter.setObjectName("tableFilter")
        self.email_reason_filter.addItem("Todos os status")
        self.email_reason_filter.currentTextChanged.connect(self._apply_email_filters)
        self.email_date_filter = QLineEdit()
        self.email_date_filter.setObjectName("tableFilter")
        self.email_date_filter.setPlaceholderText("Filtrar data")
        self.email_date_filter.textChanged.connect(self._apply_email_filters)
        self.email_size_filter = QLineEdit()
        self.email_size_filter.setObjectName("tableFilter")
        self.email_size_filter.setPlaceholderText("Filtrar tamanho")
        self.email_size_filter.textChanged.connect(self._apply_email_filters)

        self.protect_attachments_check = QCheckBox("Proteger anexos")
        self.protect_attachments_check.setChecked(True)
        self.protect_recent_check = QCheckBox("Data recente")
        self.protect_recent_check.setChecked(True)
        self.protect_important_check = QCheckBox("Importante/estrela")
        self.protect_important_check.setChecked(True)
        self.recent_days_input = QSpinBox()
        self.recent_days_input.setRange(0, 3650)
        self.recent_days_input.setValue(30)
        self.recent_days_input.setFixedWidth(92)
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
        for exception_input in (
            self.protected_senders_input,
            self.protected_domains_input,
            self.subject_keywords_input,
            self.body_keywords_input,
        ):
            exception_input.setFixedHeight(44)

    def _build_layout(self) -> None:
        root = QFrame()
        root.setObjectName("appRoot")

        self.stack = QStackedWidget()
        self.dashboard = Dashboard(self)
        self.stack.addWidget(self.dashboard)
        self.stack.addWidget(self._build_email_page())
        self.stack.addWidget(self._build_exceptions_page())
        self.stack.addWidget(self._build_accounts_page())
        self.stack.addWidget(self._build_support_page())

        self.navigation = NavigationTabs(self.nav_labels)
        self.navigation.tab_changed.connect(self.navigate_to_page)

        content_panel = QFrame()
        content_panel.setObjectName("contentPanel")
        content_layout = QVBoxLayout()
        content_layout.setContentsMargins(0, 0, 0, 0)
        content_layout.setSpacing(0)
        content_layout.addWidget(self.navigation)
        content_layout.addWidget(self.stack, 1)
        content_panel.setLayout(content_layout)

        layout = QVBoxLayout()
        layout.setContentsMargins(20, 14, 20, 14)
        layout.setSpacing(12)
        layout.addWidget(Header(self))
        layout.addWidget(content_panel, 1)
        layout.addWidget(Footer(self))
        root.setLayout(layout)
        self.setCentralWidget(root)

    def _build_email_page(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(14)
        layout.addWidget(_page_title("E-mails analisados"))
        layout.addWidget(self._build_email_filters())
        layout.addWidget(self.email_table, 1)
        page.setLayout(layout)
        return page

    def _build_email_filters(self) -> QFrame:
        filters = QFrame()
        filters.setObjectName("tableFilters")

        layout = QHBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(10)
        layout.addStretch()
        layout.addWidget(_form_label("Status"))
        layout.addWidget(self.email_reason_filter)
        layout.addWidget(_form_label("Data"))
        layout.addWidget(self.email_date_filter)
        layout.addWidget(_form_label("Tamanho"))
        layout.addWidget(self.email_size_filter)
        filters.setLayout(layout)
        return filters

    def _build_exceptions_page(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(14)
        layout.addWidget(_page_title("Exceções / Proteções"))
        layout.addWidget(self._build_exceptions_card())
        layout.addStretch()
        page.setLayout(layout)
        return page

    def _build_accounts_page(self) -> QWidget:
        page = QWidget()
        card = QFrame()
        card.setObjectName("pageCard")

        title = QLabel("Conta Gmail")
        title.setObjectName("sectionTitle")
        current_account_title = QLabel("Conta conectada no momento")
        current_account_title.setObjectName("fieldLabel")
        text = QLabel(
            "Conecte sua conta pelo login oficial do Google. Ao desconectar, "
            "o token local também será removido."
        )
        text.setObjectName("mutedText")
        text.setWordWrap(True)

        layout = QVBoxLayout()
        layout.setContentsMargins(28, 26, 28, 26)
        layout.setSpacing(16)
        layout.addWidget(title)
        layout.addWidget(current_account_title)
        layout.addWidget(self.account_page_label, 0, Qt.AlignmentFlag.AlignLeft)
        layout.addWidget(text)
        layout.addWidget(self.connect_button, 0, Qt.AlignmentFlag.AlignLeft)
        layout.addStretch()
        card.setLayout(layout)

        page_layout = QVBoxLayout()
        page_layout.setContentsMargins(0, 0, 0, 0)
        page_layout.addWidget(card, 1)
        page.setLayout(page_layout)
        return page

    def _build_support_page(self) -> QWidget:
        return _simple_page(
            "Suporte",
            "Gmail Cleaner v1.0.0\nby MacTecnology",
        )

    def _build_exceptions_card(self) -> QFrame:
        card = QFrame()
        card.setObjectName("pageCard")
        card.setMinimumHeight(270)
        layout = QVBoxLayout()
        layout.setContentsMargins(24, 20, 24, 24)
        layout.setSpacing(16)

        toggles = QHBoxLayout()
        toggles.setContentsMargins(0, 0, 0, 0)
        toggles.setSpacing(22)
        toggles.addWidget(self.protect_attachments_check)
        toggles.addWidget(self.protect_recent_check)
        toggles.addWidget(self.protect_important_check)
        toggles.addStretch()
        toggles.addWidget(_form_label("Últimos dias"))
        toggles.addWidget(self.recent_days_input)

        form = QGridLayout()
        form.setContentsMargins(0, 0, 0, 0)
        form.setHorizontalSpacing(14)
        form.setVerticalSpacing(12)
        form.addWidget(_form_label("Remetentes protegidos"), 0, 0)
        form.addWidget(self.protected_senders_input, 0, 1)
        form.addWidget(_form_label("Domínios protegidos"), 1, 0)
        form.addWidget(self.protected_domains_input, 1, 1)
        form.addWidget(_form_label("Assunto contém"), 2, 0)
        form.addWidget(self.subject_keywords_input, 2, 1)
        form.addWidget(_form_label("Corpo contém"), 3, 0)
        form.addWidget(self.body_keywords_input, 3, 1)
        form.setColumnMinimumWidth(0, 170)
        form.setColumnStretch(1, 1)
        for row in range(4):
            form.setRowMinimumHeight(row, 46)

        layout.addLayout(toggles)
        layout.addLayout(form)
        card.setLayout(layout)
        return card

    def navigate_to_page(self, page: int) -> None:
        self.stack.setCurrentIndex(page)
        self.navigation.set_active(page)

    def _prepare_table(self, table: QTableWidget, min_height: int) -> None:
        table.verticalHeader().setVisible(False)
        table.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        table.setAlternatingRowColors(True)
        table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        table.horizontalHeader().setSectionResizeMode(
            0,
            QHeaderView.ResizeMode.ResizeToContents,
        )
        table.setMinimumHeight(min_height)

    def _prepare_email_table(self) -> None:
        header = self.email_table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.Interactive)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.Fixed)
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.Fixed)
        header.setSectionResizeMode(4, QHeaderView.ResizeMode.Fixed)
        self.email_table.setColumnWidth(0, 260)
        self.email_table.setColumnWidth(2, 130)
        self.email_table.setColumnWidth(3, 96)
        self.email_table.setColumnWidth(4, 76)

    def _load_stylesheet(self) -> None:
        style_path = THEMES_DIR / "light_theme.qss"
        self.setStyleSheet(style_path.read_text(encoding="utf-8"))

    def _restore_window_placement(self) -> None:
        settings = _window_settings()
        saved_geometry = settings.value("geometry")
        was_maximized = settings.value("maximized", False, type=bool)

        if saved_geometry and self.restoreGeometry(saved_geometry):
            if was_maximized:
                self.setWindowState(self.windowState() | Qt.WindowState.WindowMaximized)
            return

        self._set_first_run_geometry()

    def _save_window_placement(self) -> None:
        settings = _window_settings()
        settings.setValue("geometry", self.saveGeometry())
        settings.setValue("maximized", self.isMaximized())

    def _set_first_run_geometry(self) -> None:
        screen = QApplication.primaryScreen()
        if screen is None:
            self.resize(MIN_WINDOW_WIDTH, MIN_WINDOW_HEIGHT)
            return

        available = screen.availableGeometry()
        width = max(
            MIN_WINDOW_WIDTH,
            min(available.width(), int(available.width() * FIRST_RUN_SCREEN_RATIO)),
        )
        height = max(
            MIN_WINDOW_HEIGHT,
            min(available.height(), int(available.height() * FIRST_RUN_SCREEN_RATIO)),
        )
        self.resize(width, height)

        frame = self.frameGeometry()
        frame.moveCenter(available.center())
        self.move(frame.topLeft())

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
        self.next_button.setVisible(next_sender)

    def set_search_running(self, running: bool, stopping: bool = False) -> None:
        if running:
            self.search_button.setText(
                "Cancelando..." if stopping else "Cancelar análise"
            )
            self.search_button.setObjectName(
                "dangerButton" if stopping else "heroButton"
            )
            self.search_button.setEnabled(not stopping)
        else:
            self.search_button.setText("🔍  Analisar")
            self.search_button.setObjectName("heroButton")
        self.search_button.style().unpolish(self.search_button)
        self.search_button.style().polish(self.search_button)

    def set_ranking_running(self, running: bool, stopping: bool = False) -> None:
        if running:
            self.rank_button.setText(
                "Cancelando..." if stopping else "Cancelar ranking"
            )
            self.rank_button.setObjectName(
                "dangerButton" if stopping else "secondaryButton"
            )
            self.rank_button.setEnabled(not stopping)
        else:
            self.rank_button.setText("Ranking por volume")
            self.rank_button.setObjectName("secondaryButton")
        self.rank_button.style().unpolish(self.rank_button)
        self.rank_button.style().polish(self.rank_button)

    def set_connected_state(self, connected: bool) -> None:
        if connected:
            self.connect_button.setText("Desconectar conta")
            self.connect_button.setObjectName("dangerButton")
            self.account_label.setText("Conta Gmail conectada")
            self.account_label.setProperty("state", "connected")
            self.account_page_label.setText("Conta Gmail conectada")
            self.account_page_label.setProperty("state", "connected")
            self.status_hint_label.setText("Conta pronta para análise.")
        else:
            self.connect_button.setText("Conectar Gmail")
            self.connect_button.setObjectName("primaryButton")
            self.account_label.setText("Nenhuma conta conectada")
            self.account_label.setProperty("state", "disconnected")
            self.account_page_label.setText("Nenhuma conta conectada")
            self.account_page_label.setProperty("state", "disconnected")
            self.status_hint_label.setText("Conecte sua conta para começar.")
        self.connect_button.style().unpolish(self.connect_button)
        self.connect_button.style().polish(self.connect_button)
        self.account_label.style().unpolish(self.account_label)
        self.account_label.style().polish(self.account_label)
        self.account_page_label.style().unpolish(self.account_page_label)
        self.account_page_label.style().polish(self.account_page_label)

    def set_account_email(self, email_address: str) -> None:
        if email_address:
            self.account_page_label.setText(email_address)
            self.account_page_label.setProperty("state", "connected")
        else:
            self.account_page_label.setText("Nenhuma conta conectada")
            self.account_page_label.setProperty("state", "disconnected")
        self.account_page_label.style().unpolish(self.account_page_label)
        self.account_page_label.style().polish(self.account_page_label)

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
        self.estimated_space_card.set_value(str(summary.get("estimated_space", "0 B")))

    def show_result_rows(self, rows: list[dict[str, object]]) -> None:
        self.result_table.setRowCount(len(rows))
        for row_index, row in enumerate(rows):
            selected = bool(row.get("selected", False))
            status = str(row.get("status", ""))
            self.result_table.setCellWidget(
                row_index, 0, _selection_indicator(selected)
            )
            self.result_table.setItem(
                row_index, 1, QTableWidgetItem(str(row["sender"]))
            )
            self.result_table.setItem(row_index, 2, QTableWidgetItem(str(row["total"])))
            self.result_table.setItem(
                row_index,
                3,
                QTableWidgetItem(str(row["cleanable_count"])),
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
            self.result_table.setItem(row_index, 6, _status_item(status))
            self.result_table.setRowHeight(row_index, 42)

    def show_protected_rows(self, rows: list[dict[str, object]]) -> None:
        self.show_email_rows(rows)

    def show_email_rows(self, rows: list[dict[str, object]]) -> None:
        self.email_rows = rows
        self._refresh_email_reason_filter(rows)
        self._apply_email_filters()

    def _refresh_email_reason_filter(self, rows: list[dict[str, object]]) -> None:
        current_filter = self.email_reason_filter.currentText()
        reasons = sorted(
            {str(row.get("reason", "")) for row in rows if row.get("reason")}
        )

        self.email_reason_filter.blockSignals(True)
        self.email_reason_filter.clear()
        self.email_reason_filter.addItem("Todos os status")
        self.email_reason_filter.addItems(reasons)
        if current_filter in reasons:
            self.email_reason_filter.setCurrentText(current_filter)
        self.email_reason_filter.blockSignals(False)

    def _apply_email_filters(self) -> None:
        reason_filter = self.email_reason_filter.currentText()
        date_filter = self.email_date_filter.text().strip().lower()
        size_filter = self.email_size_filter.text().strip().lower()

        rows = []
        for row in self.email_rows:
            reason = str(row.get("reason", ""))
            date = str(row.get("date", ""))
            size = str(row.get("size", ""))

            if reason_filter != "Todos os status" and reason != reason_filter:
                continue
            if date_filter and date_filter not in date.lower():
                continue
            if size_filter and size_filter not in size.lower():
                continue
            rows.append(row)

        self._render_email_rows(rows)

    def _render_email_rows(self, rows: list[dict[str, object]]) -> None:
        self.visible_email_rows = rows
        self.email_table.setRowCount(len(rows))
        for row_index, row in enumerate(rows):
            self.email_table.setItem(row_index, 0, QTableWidgetItem(str(row["sender"])))
            self.email_table.setItem(
                row_index, 1, QTableWidgetItem(str(row["subject"]))
            )
            self.email_table.setItem(row_index, 2, QTableWidgetItem(str(row["reason"])))
            self.email_table.setItem(row_index, 3, QTableWidgetItem(str(row["date"])))
            self.email_table.setItem(row_index, 4, QTableWidgetItem(str(row["size"])))
            self.email_table.setRowHeight(row_index, 38)
        self.email_table.viewport().update()

    def get_visible_email_message_id(self, row: int) -> str:
        if row < 0 or row >= len(self.visible_email_rows):
            return ""
        return str(self.visible_email_rows[row].get("message_id", ""))

    def show_all_email_statuses(self) -> None:
        self.email_reason_filter.setCurrentText("Todos os status")

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
                    "cleanable_count": "-",
                    "protected_count": "-",
                    "estimated_space": "-",
                    "status": (
                        "Selecionado para limpeza"
                        if sender_index == current_index
                        else "Seguro apagar"
                    ),
                }
            )
        self.show_result_rows(rows)
        self.show_email_rows(_ranking_email_rows(rows))
        self.navigate_to_page(1)

    def reset_result(self) -> None:
        self.show_summary(
            {
                "total_messages": 0,
                "found": 0,
                "cleanable": 0,
                "protected": 0,
                "unique_senders": 0,
                "estimated_space": "0 B",
            }
        )
        self.show_result_rows([])
        self.show_email_rows([])

    def confirm_move_to_trash(self, quantidade: int, protegidos: int) -> bool:
        dialog = QDialog(self)
        dialog.setWindowTitle("Confirmar limpeza")
        dialog.setModal(True)
        dialog.setMinimumWidth(520)

        icon = QLabel("!")
        icon.setObjectName("warningDialogIcon")
        icon.setAlignment(Qt.AlignmentFlag.AlignCenter)

        message = QLabel(
            (
                f"{quantidade} e-mail(s) serão movidos para a lixeira.\n\n"
                f"{protegidos} e-mail(s) foram protegidos por regras de exceção.\n\n"
                "E-mails protegidos serão preservados e nenhum e-mail será "
                "excluído permanentemente."
            )
        )
        message.setObjectName("warningDialogText")
        message.setWordWrap(True)

        content = QHBoxLayout()
        content.setContentsMargins(0, 0, 0, 0)
        content.setSpacing(18)
        content.addWidget(icon)
        content.addWidget(message, 1)

        confirm_button = QPushButton("Confirmar limpeza")
        confirm_button.setObjectName("dangerButton")
        cancel_button = QPushButton("Cancelar")
        cancel_button.setObjectName("secondaryButton")
        confirm_button.clicked.connect(dialog.accept)
        cancel_button.clicked.connect(dialog.reject)

        actions = QHBoxLayout()
        actions.setContentsMargins(0, 8, 0, 0)
        actions.setSpacing(12)
        actions.addStretch()
        actions.addWidget(cancel_button)
        actions.addWidget(confirm_button)

        layout = QVBoxLayout()
        layout.setContentsMargins(24, 22, 24, 22)
        layout.setSpacing(18)
        layout.addLayout(content)
        layout.addLayout(actions)
        dialog.setLayout(layout)

        return dialog.exec() == QDialog.DialogCode.Accepted


class Header(QFrame):
    def __init__(self, window: MainWindow) -> None:
        super().__init__()
        self.setObjectName("header")

        icon = QLabel("✉")
        icon.setObjectName("brandIcon")
        icon.setAlignment(Qt.AlignmentFlag.AlignCenter)
        if LOGO_FILE.exists():
            logo = QPixmap(str(LOGO_FILE))
            if not logo.isNull():
                icon.setPixmap(
                    logo.scaled(
                        54,
                        54,
                        Qt.AspectRatioMode.KeepAspectRatio,
                        Qt.TransformationMode.SmoothTransformation,
                    )
                )

        title = QLabel(
            '<span style="color:#071A3D">Gmail</span> '
            '<span style="color:#1677FF">Cleaner</span>'
        )
        title.setObjectName("brandTitle")
        slogan = QLabel("ORGANIZE. PROTEJA. LIMPE COM\nSEGURANÇA.")
        slogan.setObjectName("brandSlogan")
        byline = QLabel(
            'by&nbsp;&nbsp;<span style="color:#1677FF;font-weight:800">'
            "MacTecnology</span>"
        )
        byline.setObjectName("brandByline")

        brand_title = QHBoxLayout()
        brand_title.setContentsMargins(0, 0, 0, 0)
        brand_title.setSpacing(16)
        brand_title.addWidget(icon)
        brand_title.addWidget(title)
        brand_title.addStretch()

        text_layout = QVBoxLayout()
        text_layout.setContentsMargins(0, 0, 0, 0)
        text_layout.setSpacing(22)
        text_layout.addLayout(brand_title)
        text_layout.addWidget(slogan)
        text_layout.addWidget(byline)
        text_layout.addStretch()

        summary = SummaryCard(window)

        layout = QHBoxLayout()
        layout.setContentsMargins(28, 22, 28, 18)
        layout.setSpacing(36)
        layout.addLayout(text_layout, 0)
        layout.addWidget(summary, 1)
        self.setLayout(layout)


class NavigationTabs(QFrame):
    tab_changed = pyqtSignal(int)

    def __init__(self, labels: list[str]) -> None:
        super().__init__()
        self.setObjectName("navigation")
        self.buttons: list[QPushButton] = []
        icons = ["⌂", "✉", "♢", "♙", "?"]

        layout = QHBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        for index, label in enumerate(labels):
            button = QPushButton(f"{icons[index]}  {label}")
            button.setObjectName("tabActive" if index == 0 else "tabButton")
            button.setFocusPolicy(Qt.FocusPolicy.NoFocus)
            button.clicked.connect(
                lambda _checked=False, page=index: self.tab_changed.emit(page)
            )
            button.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
            self.buttons.append(button)
            layout.addWidget(button)
        self.setLayout(layout)

    def set_active(self, active_index: int) -> None:
        for index, button in enumerate(self.buttons):
            button.setObjectName("tabActive" if index == active_index else "tabButton")
            button.style().unpolish(button)
            button.style().polish(button)


class Dashboard(QWidget):
    def __init__(self, window: MainWindow) -> None:
        super().__init__()

        title = QLabel("Pronto para liberar espaço")
        title.setObjectName("heroTitle")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)

        search_bar = QFrame()
        search_bar.setObjectName("analysisSearchBar")
        search_icon = QLabel("⌕")
        search_icon.setObjectName("analysisSearchIcon")
        search_icon.setAlignment(Qt.AlignmentFlag.AlignCenter)
        window.sender_input.setPlaceholderText("Buscar remetente ou domínio")
        window.sender_input.setObjectName("analysisSearchInput")
        window.sender_input.setMinimumWidth(560)
        window.search_button.setFixedWidth(176)
        window.rank_button.setFixedWidth(214)

        search_layout = QHBoxLayout()
        search_layout.setContentsMargins(18, 0, 0, 0)
        search_layout.setSpacing(12)
        search_layout.addWidget(search_icon)
        search_layout.addWidget(window.sender_input, 1)
        search_layout.addWidget(window.search_button)
        search_layout.addWidget(window.rank_button)
        search_layout.addWidget(window.next_button)
        search_bar.setLayout(search_layout)

        cards = QHBoxLayout()
        cards.setContentsMargins(0, 0, 0, 0)
        cards.setSpacing(20)
        cards.addWidget(
            AnalysisActionCard(
                "🏆",
                "Ranking de remetentes",
                "Veja os remetentes que mais ocupam espaço na sua conta.",
                "Ver ranking",
                "blue",
                window.rank_button.click,
            )
        )
        cards.addWidget(
            AnalysisActionCard(
                "🛡",
                "Proteções ativas",
                "Regras e filtros que protegem anexos e e-mails importantes.",
                "Ver exceções",
                "green",
                lambda: window.navigate_to_page(2),
            )
        )
        cards.addWidget(
            AnalysisActionCard(
                "🧹",
                "E-mails analisados",
                "Depois da análise, revise a lista detalhada antes de limpar.",
                "Ver e-mails",
                "orange",
                lambda: window.navigate_to_page(1),
            )
        )

        content = QFrame()
        content.setObjectName("analysisCenter")
        content_layout = QVBoxLayout()
        content_layout.setContentsMargins(0, 0, 0, 0)
        content_layout.setSpacing(28)
        content_layout.addWidget(title, 0, Qt.AlignmentFlag.AlignCenter)
        content_layout.addWidget(search_bar, 0, Qt.AlignmentFlag.AlignCenter)
        content_layout.addLayout(cards)
        content_layout.addWidget(window.progress_bar)
        content.setLayout(content_layout)

        layout = QVBoxLayout()
        layout.setContentsMargins(60, 26, 60, 12)
        layout.setSpacing(0)
        layout.addWidget(content, 0, Qt.AlignmentFlag.AlignCenter)
        layout.addStretch()
        self.setLayout(layout)


class AnalysisActionCard(QFrame):
    def __init__(
        self,
        icon: str,
        title: str,
        text: str,
        button_text: str,
        tone: str,
        action,
    ) -> None:
        super().__init__()
        self.setObjectName("analysisActionCard")
        self.setProperty("tone", tone)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self.setFixedHeight(150)

        icon_label = QLabel(icon)
        icon_label.setObjectName("analysisActionIcon")
        icon_label.setAlignment(Qt.AlignmentFlag.AlignCenter)

        title_label = QLabel(title)
        title_label.setObjectName("analysisActionTitle")
        text_label = QLabel(text)
        text_label.setObjectName("analysisActionText")
        text_label.setWordWrap(True)

        text_layout = QVBoxLayout()
        text_layout.setContentsMargins(0, 0, 0, 0)
        text_layout.setSpacing(4)
        text_layout.addWidget(title_label)
        text_layout.addWidget(text_label)
        text_layout.addStretch()

        body = QHBoxLayout()
        body.setContentsMargins(0, 0, 0, 0)
        body.setSpacing(18)
        body.addWidget(icon_label)
        body.addLayout(text_layout, 1)

        button = QPushButton(button_text)
        button.setObjectName(f"analysisCardButton{tone.title()}")
        button.clicked.connect(action)

        layout = QVBoxLayout()
        layout.setContentsMargins(18, 14, 18, 14)
        layout.setSpacing(10)
        layout.addLayout(body)
        layout.addWidget(button)
        self.setLayout(layout)


class SummaryCard(QFrame):
    def __init__(self, window: MainWindow) -> None:
        super().__init__()
        self.setObjectName("summaryCard")
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self.setMinimumWidth(760)
        self.setMaximumWidth(900)
        self.setMinimumHeight(174)

        title_icon = QLabel("⌁")
        title_icon.setObjectName("summaryTitleIcon")
        title = QLabel("Resumo da conta")
        title.setObjectName("summaryTitle")

        header = QHBoxLayout()
        header.setContentsMargins(24, 14, 24, 12)
        header.setSpacing(10)
        header.addWidget(title_icon)
        header.addWidget(title)
        header.addStretch()
        header.addWidget(window.trash_button)

        metrics = QHBoxLayout()
        metrics.setContentsMargins(28, 12, 28, 16)
        metrics.setSpacing(0)
        for index, metric in enumerate(
            [
                window.total_messages_card,
                window.safe_card,
                window.estimated_space_card,
                window.protected_card,
            ]
        ):
            metrics.addWidget(metric, 1)
            if index < 3:
                metrics.addWidget(_divider())

        layout = QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        layout.addLayout(header)
        layout.addWidget(_horizontal_rule())
        layout.addLayout(metrics)
        self.setLayout(layout)


class SummaryMetric(QFrame):
    def __init__(self, icon: str, value: str, title: str, color: str) -> None:
        super().__init__()
        self.setObjectName("summaryMetric")
        self.setProperty("tone", color)
        self.setMinimumHeight(78)

        icon_label = QLabel(icon)
        icon_label.setObjectName("metricIcon")
        icon_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.value_label = QLabel(value)
        self.value_label.setObjectName("metricValue")
        self.value_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title_label = QLabel(title)
        title_label.setObjectName("metricTitle")
        title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)

        layout = QVBoxLayout()
        layout.setContentsMargins(12, 0, 12, 0)
        layout.setSpacing(6)
        layout.addWidget(icon_label)
        layout.addWidget(self.value_label)
        layout.addWidget(title_label)
        self.setLayout(layout)

    def set_value(self, value: str) -> None:
        self.value_label.setText(value)


class Footer(QFrame):
    def __init__(self, window: MainWindow) -> None:
        super().__init__()
        self.setObjectName("footer")

        separator_right = QLabel("|")
        separator_right.setObjectName("footerSeparator")

        version = QLabel("v1.0.0")
        version.setObjectName("footerText")

        status_text = QVBoxLayout()
        status_text.setContentsMargins(0, 0, 0, 0)
        status_text.setSpacing(2)
        status_text.addWidget(window.status_label)
        status_text.addWidget(window.status_hint_label)

        layout = QHBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(14)
        layout.addWidget(window.status_dot)
        layout.addLayout(status_text)
        layout.addStretch()
        layout.addWidget(version)
        layout.addWidget(separator_right)
        layout.addWidget(window.account_label)
        self.setLayout(layout)


def _simple_page(title: str, text: str) -> QWidget:
    page = QWidget()
    card = QFrame()
    card.setObjectName("pageCard")
    title_label = QLabel(title)
    title_label.setObjectName("sectionTitle")
    text_label = QLabel(text)
    text_label.setObjectName("mutedText")
    text_label.setWordWrap(True)

    card_layout = QVBoxLayout()
    card_layout.setContentsMargins(28, 26, 28, 26)
    card_layout.setSpacing(14)
    card_layout.addWidget(title_label)
    card_layout.addWidget(text_label)
    card_layout.addStretch()
    card.setLayout(card_layout)

    page_layout = QVBoxLayout()
    page_layout.setContentsMargins(0, 0, 0, 0)
    page_layout.addWidget(card, 1)
    page.setLayout(page_layout)
    return page


def _page_title(text: str) -> QLabel:
    title = QLabel(text)
    title.setObjectName("pageSectionTitle")
    return title


def _divider() -> QFrame:
    divider = QFrame()
    divider.setObjectName("metricDivider")
    divider.setFixedWidth(1)
    return divider


def _horizontal_rule() -> QFrame:
    rule = QFrame()
    rule.setObjectName("horizontalRule")
    rule.setFixedHeight(1)
    return rule


def _selection_indicator(checked: bool) -> QLabel:
    label = QLabel("✓" if checked else "")
    label.setObjectName("selectionIndicator")
    label.setAlignment(Qt.AlignmentFlag.AlignCenter)
    return label


def _status_item(status: str) -> QTableWidgetItem:
    item = QTableWidgetItem(status)
    colors = {
        "Seguro apagar": QColor("#DCFCE7"),
        "Selecionado para limpeza": QColor("#DBEAFE"),
        "Atencao: possui anexos": QColor("#FEF3C7"),
        "Atenção: possui anexos": QColor("#FEF3C7"),
        "Protegido": QColor("#F1F5F9"),
    }
    item.setForeground(QColor("#0F172A"))
    item.setBackground(colors.get(status, QColor("#FFFFFF")))
    return item


def _ranking_email_rows(rows: list[dict[str, object]]) -> list[dict[str, object]]:
    return [
        {
            "sender": row["sender"],
            "subject": "-",
            "reason": f"{row['total']} e-mail(s) no remetente",
            "date": "-",
            "size": row["estimated_space"],
        }
        for row in rows
    ]


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


def _window_settings() -> QSettings:
    return QSettings("MacTecnology", "GmailCleaner")
