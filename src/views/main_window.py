from __future__ import annotations

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QLabel,
    QListWidget,
    QListWidgetItem,
    QMainWindow,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from src.services.gmail_service import pegar_assunto, pegar_data, pegar_remetente


class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()

        self.setWindowTitle("Gmail Cleaner")
        self.setMinimumSize(720, 480)

        self.title_label = QLabel("Gmail Cleaner")
        self.title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.title_label.setObjectName("titleLabel")

        self.connect_button = QPushButton("Conectar Gmail")
        self.status_label = QLabel("Status: desconectado")
        self.status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.load_emails_button = QPushButton("Carregar e-mails")
        self.load_emails_button.setEnabled(False)

        self.email_list = QListWidget()

        layout = QVBoxLayout()
        layout.addWidget(self.title_label)
        layout.addWidget(self.connect_button)
        layout.addWidget(self.status_label)
        layout.addWidget(self.load_emails_button)
        layout.addWidget(self.email_list)

        container = QWidget()
        container.setLayout(layout)
        self.setCentralWidget(container)

        self.setStyleSheet(
            """
            QMainWindow {
                background: #f6f8fa;
            }

            QLabel#titleLabel {
                color: #1f2328;
                font-size: 26px;
                font-weight: 700;
                padding: 16px 0;
            }

            QPushButton {
                background: #0969da;
                border: 0;
                border-radius: 6px;
                color: white;
                font-size: 15px;
                font-weight: 600;
                min-height: 38px;
                padding: 0 16px;
            }

            QPushButton:disabled {
                background: #8c959f;
            }

            QLabel {
                color: #57606a;
                font-size: 14px;
                padding: 8px 0;
            }

            QListWidget {
                background: white;
                border: 1px solid #d0d7de;
                border-radius: 6px;
                color: #24292f;
                font-size: 13px;
                padding: 8px;
            }
            """
        )

    def set_status(self, message: str) -> None:
        self.status_label.setText(f"Status: {message}")

    def set_buttons_enabled(self, connect: bool, load: bool) -> None:
        self.connect_button.setEnabled(connect)
        self.load_emails_button.setEnabled(load)

    def show_emails(self, emails) -> None:
        self.email_list.clear()

        for email in emails:
            item_text = (
                f"{pegar_assunto(email)}\n"
                f"De: {pegar_remetente(email)}\n"
                f"Data: {pegar_data(email)}"
            )
            self.email_list.addItem(QListWidgetItem(item_text))
