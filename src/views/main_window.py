from __future__ import annotations

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)


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

        self.sender_input = QLineEdit()
        self.sender_input.setPlaceholderText("Digite o remetente")

        self.search_button = QPushButton("Buscar")
        self.search_button.setEnabled(False)

        self.trash_button = QPushButton("Mover para lixeira")
        self.trash_button.setEnabled(False)

        self.result_table = QTableWidget(1, 2)
        self.result_table.setHorizontalHeaderLabels(["Remetente", "Quantidade"])
        self.result_table.verticalHeader().setVisible(False)
        self.result_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.result_table.setSelectionMode(QTableWidget.SelectionMode.NoSelection)
        self.result_table.setItem(0, 0, QTableWidgetItem("-"))
        self.result_table.setItem(0, 1, QTableWidgetItem("0"))
        self.result_table.horizontalHeader().setStretchLastSection(True)

        form_layout = QHBoxLayout()
        form_layout.addWidget(self.sender_input)
        form_layout.addWidget(self.search_button)

        layout = QVBoxLayout()
        layout.addWidget(self.title_label)
        layout.addWidget(self.connect_button)
        layout.addWidget(self.status_label)
        layout.addLayout(form_layout)
        layout.addWidget(self.result_table)
        layout.addWidget(self.trash_button)

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

            QLineEdit {
                background: white;
                border: 1px solid #d0d7de;
                border-radius: 6px;
                color: #24292f;
                font-size: 14px;
                min-height: 36px;
                padding: 0 10px;
            }

            QLabel {
                color: #57606a;
                font-size: 14px;
                padding: 8px 0;
            }

            QTableWidget {
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

    def set_buttons_enabled(
        self,
        connect: bool,
        search: bool,
        trash: bool = False,
    ) -> None:
        self.connect_button.setEnabled(connect)
        self.search_button.setEnabled(search)
        self.trash_button.setEnabled(trash)

    def get_sender(self) -> str:
        return self.sender_input.text().strip()

    def show_result(self, remetente: str, quantidade: int) -> None:
        self.result_table.setItem(0, 0, QTableWidgetItem(remetente))
        self.result_table.setItem(0, 1, QTableWidgetItem(str(quantidade)))

    def reset_result(self) -> None:
        self.show_result("-", 0)

    def confirm_move_to_trash(self, quantidade: int) -> bool:
        resposta = QMessageBox.question(
            self,
            "Confirmar envio para lixeira",
            f"Mover {quantidade} e-mail(s) para a lixeira?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        return resposta == QMessageBox.StandardButton.Yes
