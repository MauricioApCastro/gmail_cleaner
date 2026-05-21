from __future__ import annotations

from PyQt6.QtCore import Qt, QTimer, pyqtSignal
from PyQt6.QtGui import QColor, QIcon, QPixmap
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


class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()

        self.setWindowTitle("Gmail Cleaner")
        if ICON_FILE.exists():
            self.setWindowIcon(QIcon(str(ICON_FILE)))
        self.setMinimumSize(980, 680)
        self.resize(1180, 760)

        self.current_theme = "light"
        self.nav_labels = [
            "Visão Geral",
            "Histórico",
            "Exceções",
            "Contas",
            "Configurações",
            "Suporte",
        ]

        self._create_shared_widgets()
        self._build_layout()
        self._load_stylesheet()
        self.set_status("Não conectado", "offline")
        self.set_connected_state(False)
        self.reset_result()

    def _create_shared_widgets(self) -> None:
        self.connect_button = QPushButton("Conectar Gmail")
        self.connect_button.setObjectName("primaryButton")

        self.search_button = QPushButton("🔍  Analisar")
        self.search_button.setObjectName("heroButton")
        self.search_button.setEnabled(False)

        self.rank_button = QPushButton("Ranking por volume")
        self.rank_button.setObjectName("secondaryButton")
        self.rank_button.setEnabled(False)

        self.next_button = QPushButton("Pré-visualizar limpeza")
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
        self.account_label = QLabel("Nenhuma conta conectada")
        self.account_label.setObjectName("footerText")

        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        self.progress_bar.setVisible(False)
        self.progress_bar.setTextVisible(False)

        self.total_messages_card = SummaryMetric("✉", "0", "Total de emails", "blue")
        self.safe_card = SummaryMetric("⌫", "0", "Podem ser removidos", "green")
        self.estimated_space_card = SummaryMetric(
            "□", "0 B", "Espaço recuperável", "orange"
        )
        self.protected_card = SummaryMetric("◇", "0", "Protegidos", "purple")

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

        self.protected_table = QTableWidget(0, 5)
        self.protected_table.setHorizontalHeaderLabels(
            ["Remetente", "Assunto", "Motivo", "Data", "Tamanho"]
        )
        self._prepare_table(self.protected_table, min_height=380)

        self.protect_attachments_check = QCheckBox("Proteger anexos")
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

    def _build_layout(self) -> None:
        root = QFrame()
        root.setObjectName("appRoot")

        self.stack = QStackedWidget()
        self.dashboard = Dashboard(self)
        self.stack.addWidget(self.dashboard)
        self.stack.addWidget(self._build_history_page())
        self.stack.addWidget(self._build_exceptions_page())
        self.stack.addWidget(self._build_accounts_page())
        self.stack.addWidget(self._build_settings_page())
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
        layout.addWidget(Header())
        layout.addWidget(content_panel, 1)
        layout.addWidget(Footer(self))
        root.setLayout(layout)
        self.setCentralWidget(root)

    def _build_history_page(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(14)
        layout.addWidget(_page_title("Remetentes por quantidade"))
        layout.addWidget(self.result_table, 1)
        page.setLayout(layout)
        return page

    def _build_exceptions_page(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(14)
        layout.addWidget(_page_title("Exceções / Proteções"))
        layout.addWidget(self._build_exceptions_card())
        layout.addWidget(_page_title("Protegidos"))
        layout.addWidget(self.protected_table, 1)
        page.setLayout(layout)
        return page

    def _build_accounts_page(self) -> QWidget:
        page = QWidget()
        card = QFrame()
        card.setObjectName("pageCard")

        title = QLabel("Conta Gmail")
        title.setObjectName("sectionTitle")
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
        layout.addWidget(text)
        layout.addWidget(self.connect_button, 0, Qt.AlignmentFlag.AlignLeft)
        layout.addStretch()
        card.setLayout(layout)

        page_layout = QVBoxLayout()
        page_layout.setContentsMargins(0, 0, 0, 0)
        page_layout.addWidget(card, 1)
        page.setLayout(page_layout)
        return page

    def _build_settings_page(self) -> QWidget:
        return _simple_page(
            "Configurações",
            "Tema claro fixo, proteção por anexos ativada por padrão e limpeza sempre "
            "com confirmação antes de mover mensagens para a lixeira.",
        )

    def _build_support_page(self) -> QWidget:
        return _simple_page(
            "Suporte",
            "Gmail Cleaner v1.0.0\nby MacTecnology",
        )

    def _build_exceptions_card(self) -> QFrame:
        card = QFrame()
        card.setObjectName("pageCard")
        layout = QGridLayout()
        layout.setContentsMargins(24, 22, 24, 24)
        layout.setHorizontalSpacing(12)
        layout.setVerticalSpacing(12)

        layout.addWidget(self.protect_attachments_check, 0, 0)
        layout.addWidget(self.protect_recent_check, 0, 1)
        layout.addWidget(_form_label("Últimos dias"), 0, 2)
        layout.addWidget(self.recent_days_input, 0, 3)
        layout.addWidget(self.protect_important_check, 1, 0)
        layout.addWidget(_form_label("Remetentes protegidos"), 2, 0)
        layout.addWidget(self.protected_senders_input, 2, 1, 1, 3)
        layout.addWidget(_form_label("Domínios protegidos"), 3, 0)
        layout.addWidget(self.protected_domains_input, 3, 1, 1, 3)
        layout.addWidget(_form_label("Assunto contém"), 4, 0)
        layout.addWidget(self.subject_keywords_input, 4, 1, 1, 3)
        layout.addWidget(_form_label("Corpo contém"), 5, 0)
        layout.addWidget(self.body_keywords_input, 5, 1, 1, 3)
        layout.setColumnStretch(1, 1)
        card.setLayout(layout)
        return card

    def navigate_to_page(self, page: int) -> None:
        self.stack.setCurrentIndex(page)
        self.navigation.set_active(page)

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
        style_path = THEMES_DIR / "light_theme.qss"
        self.setStyleSheet(style_path.read_text(encoding="utf-8"))

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
            self.account_label.setText("Conta Gmail conectada")
        else:
            self.connect_button.setText("Conectar Gmail")
            self.connect_button.setObjectName("primaryButton")
            self.account_label.setText("Nenhuma conta conectada")
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
        self.estimated_space_card.set_value(str(summary.get("estimated_space", "0 B")))

    def show_result_rows(self, rows: list[dict[str, object]]) -> None:
        self.result_table.setRowCount(len(rows))
        for row_index, row in enumerate(rows):
            selected = bool(row.get("selected", False))
            status = str(row.get("status", ""))
            self.result_table.setItem(row_index, 0, _checkbox_item(selected))
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
        self.protected_table.setRowCount(len(rows))
        for row_index, row in enumerate(rows):
            self.protected_table.setItem(
                row_index, 0, QTableWidgetItem(str(row["sender"]))
            )
            self.protected_table.setItem(
                row_index, 1, QTableWidgetItem(str(row["subject"]))
            )
            self.protected_table.setItem(
                row_index, 2, QTableWidgetItem(str(row["reason"]))
            )
            self.protected_table.setItem(
                row_index, 3, QTableWidgetItem(str(row["date"]))
            )
            self.protected_table.setItem(
                row_index, 4, QTableWidgetItem(str(row["size"]))
            )
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
        self.show_protected_rows([])

    def confirm_move_to_trash(self, quantidade: int, protegidos: int) -> bool:
        resposta = QMessageBox.question(
            self,
            "Confirmar limpeza",
            (
                f"{quantidade} e-mail(s) serão movidos para a lixeira.\n\n"
                f"{protegidos} e-mail(s) foram protegidos por regras de exceção.\n\n"
                "E-mails protegidos serão preservados e nenhum e-mail será "
                "excluído permanentemente.\n\n"
                "Deseja continuar?"
            ),
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        return resposta == QMessageBox.StandardButton.Yes


class TopBar(QFrame):
    def __init__(self) -> None:
        super().__init__()
        self.setObjectName("topBar")

        title = QLabel("Gmail Cleaner")
        title.setObjectName("topTitle")

        layout = QHBoxLayout()
        layout.setContentsMargins(2, 0, 2, 0)
        layout.setSpacing(0)
        layout.addWidget(title)
        layout.addStretch()
        self.setLayout(layout)


class Header(QFrame):
    def __init__(self) -> None:
        super().__init__()
        self.setObjectName("header")

        title = QLabel(
            '<span style="color:#0F172A">Gmail</span> '
            '<span style="color:#0D6EFD">Cleaner</span>'
        )
        title.setObjectName("brandTitle")
        slogan = QLabel("ORGANIZE. PROTEJA. LIMPE COM SEGURANÇA.")
        slogan.setObjectName("brandSlogan")
        slogan.setWordWrap(True)
        byline = QLabel(
            'by&nbsp;&nbsp;<span style="color:#0D6EFD;font-weight:800">'
            "MacTecnology</span>"
        )
        byline.setObjectName("brandByline")

        text_layout = QVBoxLayout()
        text_layout.setContentsMargins(0, 0, 0, 0)
        text_layout.setSpacing(6)
        text_layout.addWidget(title)
        text_layout.addWidget(slogan)
        text_layout.addWidget(byline)

        badge = SecurityBadge()

        layout = QHBoxLayout()
        layout.setContentsMargins(40, 8, 40, 8)
        layout.setSpacing(28)
        layout.addLayout(text_layout, 1)
        layout.addWidget(badge)
        self.setLayout(layout)


class SecurityBadge(QFrame):
    def __init__(self) -> None:
        super().__init__()
        self.setObjectName("securityBadge")

        icon = QLabel("✓")
        icon.setObjectName("securityIcon")
        icon.setAlignment(Qt.AlignmentFlag.AlignCenter)

        title = QLabel("Seguro e confiável")
        title.setObjectName("securityTitle")
        detail = QLabel("Conecta usando o login oficial do Google")
        detail.setObjectName("securityText")

        text_layout = QVBoxLayout()
        text_layout.setContentsMargins(0, 0, 0, 0)
        text_layout.setSpacing(5)
        text_layout.addWidget(title)
        text_layout.addWidget(detail)

        layout = QHBoxLayout()
        layout.setContentsMargins(18, 14, 18, 14)
        layout.setSpacing(14)
        layout.addWidget(icon)
        layout.addLayout(text_layout)
        self.setLayout(layout)


class NavigationTabs(QFrame):
    tab_changed = pyqtSignal(int)

    def __init__(self, labels: list[str]) -> None:
        super().__init__()
        self.setObjectName("navigation")
        self.buttons: list[QPushButton] = []
        icons = ["⌂", "◷", "◇", "✉", "⚙", "?"]

        layout = QHBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        for index, label in enumerate(labels):
            button = QPushButton(f"{icons[index]}  {label}")
            button.setObjectName("tabActive" if index == 0 else "tabButton")
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

        title = QLabel("Apague milhares de emails")
        title.setObjectName("heroTitle")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)

        subtitle = QLabel(
            "Encontre e remova emails desnecessários com segurança.\n"
            "Proteja o que é importante. Libere espaço na sua conta."
        )
        subtitle.setObjectName("heroSubtitle")
        subtitle.setAlignment(Qt.AlignmentFlag.AlignCenter)

        input_row = QFrame()
        input_row.setObjectName("searchRow")
        input_layout = QHBoxLayout()
        input_layout.setContentsMargins(0, 0, 0, 0)
        input_layout.setSpacing(10)
        input_layout.addWidget(window.sender_input, 1)
        input_layout.addWidget(window.rank_button)
        input_row.setLayout(input_layout)

        actions = QHBoxLayout()
        actions.setContentsMargins(0, 0, 0, 0)
        actions.addStretch()
        actions.addWidget(window.search_button)
        actions.addStretch()

        cleanup_actions = QHBoxLayout()
        cleanup_actions.setContentsMargins(0, 0, 0, 0)
        cleanup_actions.addStretch()
        cleanup_actions.addWidget(window.trash_button)
        cleanup_actions.addStretch()

        layout = QVBoxLayout()
        layout.setContentsMargins(18, 30, 18, 8)
        layout.setSpacing(16)
        layout.addWidget(title)
        layout.addWidget(subtitle)
        layout.addWidget(input_row, 0, Qt.AlignmentFlag.AlignCenter)
        layout.addLayout(actions)
        layout.addWidget(window.progress_bar)
        layout.addLayout(cleanup_actions)
        layout.addSpacing(10)
        layout.addWidget(SummaryCard(window), 0, Qt.AlignmentFlag.AlignCenter)
        layout.addStretch()
        self.setLayout(layout)


class SummaryCard(QFrame):
    def __init__(self, window: MainWindow) -> None:
        super().__init__()
        self.setObjectName("summaryCard")
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)

        title_icon = QLabel("⌁")
        title_icon.setObjectName("summaryTitleIcon")
        title = QLabel("Resumo da conta")
        title.setObjectName("summaryTitle")

        header = QHBoxLayout()
        header.setContentsMargins(24, 18, 24, 16)
        header.setSpacing(10)
        header.addWidget(title_icon)
        header.addWidget(title)
        header.addStretch()

        metrics = QHBoxLayout()
        metrics.setContentsMargins(28, 22, 28, 26)
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
        layout.setSpacing(8)
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

        separator_left = QLabel("|")
        separator_left.setObjectName("footerSeparator")
        separator_right = QLabel("|")
        separator_right.setObjectName("footerSeparator")

        shield = QLabel("◇")
        shield.setObjectName("footerIcon")
        version = QLabel("v1.0.0")
        version.setObjectName("footerText")
        about = QLabel("Sobre o Gmail Cleaner")
        about.setObjectName("footerText")

        layout = QHBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(14)
        layout.addWidget(window.status_dot)
        layout.addWidget(window.status_label)
        layout.addWidget(separator_left)
        layout.addWidget(shield)
        layout.addWidget(window.account_label)
        layout.addStretch()
        layout.addWidget(version)
        layout.addWidget(separator_right)
        layout.addWidget(about)
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


def _checkbox_item(checked: bool) -> QTableWidgetItem:
    item = QTableWidgetItem()
    item.setFlags(
        Qt.ItemFlag.ItemIsEnabled
        | Qt.ItemFlag.ItemIsUserCheckable
        | Qt.ItemFlag.ItemIsSelectable
    )
    item.setCheckState(Qt.CheckState.Checked if checked else Qt.CheckState.Unchecked)
    return item


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
