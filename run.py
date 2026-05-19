"""Application entry point for Gmail Cleaner."""

import sys

from PyQt6.QtWidgets import QApplication

from src.controllers.main_controller import MainController
from src.views.main_window import MainWindow


def main() -> None:
    _configure_stdout()
    app = QApplication(sys.argv)
    window = MainWindow()
    controller = MainController(window)
    window.show()
    sys.exit(app.exec())


def _configure_stdout() -> None:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")


if __name__ == "__main__":
    main()
