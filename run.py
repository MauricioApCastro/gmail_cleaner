"""Application entry point for Gmail Cleaner."""

import sys


def main() -> None:
    _configure_stdout()

    if "--trash-sender-test" in sys.argv:
        run_trash_sender_test()
        return

    from PyQt6.QtWidgets import QApplication

    from src.controllers.main_controller import MainController
    from src.views.main_window import MainWindow

    app = QApplication(sys.argv)
    window = MainWindow()
    controller = MainController(window)
    window.show()
    sys.exit(app.exec())


def _configure_stdout() -> None:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")


def run_trash_sender_test() -> None:
    from src.services.gmail_actions import (
        buscar_emails_por_remetente,
        mover_emails_para_lixeira,
    )
    from src.services.gmail_auth import get_gmail_service

    remetente = input("Remetente para buscar: ").strip()
    if not remetente:
        print("Nenhum remetente informado.")
        return

    print("Conectando ao Gmail...")
    service = get_gmail_service()

    print(f"Buscando e-mails com query: from:{remetente}")
    message_ids = buscar_emails_por_remetente(service, remetente)
    total = len(message_ids)
    print(f"Quantidade encontrada: {total}")

    if total == 0:
        return

    confirmacao = input("Digite SIM para mover todos para a lixeira: ").strip()
    if confirmacao != "SIM":
        print("Operacao cancelada.")
        return

    movidos = mover_emails_para_lixeira(service, message_ids)
    print(f"Concluido. {movidos} e-mail(s) movido(s) para a lixeira.")


if __name__ == "__main__":
    main()
