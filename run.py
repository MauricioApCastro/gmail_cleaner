"""Application entry point for Gmail Cleaner."""

import sys


def main() -> None:
    _configure_stdout()

    if "--trash-sender-test" in sys.argv:
        run_trash_sender_test()
        return

    from PyQt6.QtCore import Qt, QTimer
    from PyQt6.QtGui import QColor, QIcon, QPainter, QPixmap
    from PyQt6.QtWidgets import QApplication, QSplashScreen

    from src.config.settings import ICON_FILE, LOGO_FILE
    from src.controllers.main_controller import MainController
    from src.ui.main_window import MainWindow

    app = QApplication(sys.argv)
    _set_windows_app_id()
    if ICON_FILE.exists():
        app.setWindowIcon(QIcon(str(ICON_FILE)))

    screen_size = app.primaryScreen().availableGeometry()
    splash_size = (
        min(1100, int(screen_size.width() * 0.72)),
        min(700, int(screen_size.height() * 0.72)),
    )
    splash = _create_splash_screen(
        QPixmap,
        QPainter,
        QColor,
        Qt,
        QSplashScreen,
        LOGO_FILE,
        splash_size,
    )
    splash.show()
    app.processEvents()

    window = MainWindow()
    controller = MainController(window)
    window.controller = controller

    def show_main_window() -> None:
        splash.finish(window)
        window.show()

    QTimer.singleShot(1200, show_main_window)
    sys.exit(app.exec())


def _configure_stdout() -> None:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")


def _set_windows_app_id() -> None:
    if sys.platform != "win32":
        return

    try:
        import ctypes

        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(
            "MacTecnology.GmailCleaner"
        )
    except Exception:
        pass


def _create_splash_screen(
    pixmap_class,
    painter_class,
    color_class,
    qt_class,
    splash_class,
    logo_file,
    splash_size,
):
    width, height = splash_size
    canvas = pixmap_class(width, height)
    canvas.fill(color_class("#f8fafc"))

    painter = painter_class(canvas)
    painter.setRenderHint(painter_class.RenderHint.Antialiasing)

    painter.setPen(color_class("#dbeafe"))
    painter.setBrush(color_class("#eff6ff"))
    painter.drawRoundedRect(32, 32, width - 64, height - 64, 28, 28)

    if logo_file.exists():
        logo = pixmap_class(str(logo_file))
        if not logo.isNull():
            logo_size = max(190, min(300, int(height * 0.38)))
            logo = logo.scaled(
                logo_size,
                logo_size,
                qt_class.AspectRatioMode.KeepAspectRatio,
                qt_class.TransformationMode.SmoothTransformation,
            )
            x = (canvas.width() - logo.width()) // 2
            painter.drawPixmap(x, int(height * 0.16), logo)

    painter.setPen(color_class("#0f172a"))
    title_font = painter.font()
    title_font.setPointSize(max(28, int(height * 0.065)))
    title_font.setBold(True)
    painter.setFont(title_font)
    painter.drawText(
        0,
        int(height * 0.58),
        canvas.width(),
        int(height * 0.09),
        qt_class.AlignmentFlag.AlignCenter,
        "Gmail Cleaner",
    )

    painter.setPen(color_class("#475569"))
    subtitle_font = painter.font()
    subtitle_font.setPointSize(max(12, int(height * 0.026)))
    subtitle_font.setBold(False)
    painter.setFont(subtitle_font)
    painter.drawText(
        0,
        int(height * 0.69),
        canvas.width(),
        int(height * 0.06),
        qt_class.AlignmentFlag.AlignCenter,
        "Carregando ambiente seguro...",
    )

    painter.setPen(color_class("#0d6efd"))
    loading_font = painter.font()
    loading_font.setPointSize(max(9, int(height * 0.018)))
    loading_font.setBold(True)
    painter.setFont(loading_font)
    painter.drawText(
        0,
        int(height * 0.82),
        canvas.width(),
        int(height * 0.04),
        qt_class.AlignmentFlag.AlignCenter,
        "ORGANIZE. PROTEJA. LIMPE COM SEGURANÇA.",
    )
    painter.end()

    splash = splash_class(canvas)
    splash.setWindowFlag(qt_class.WindowType.FramelessWindowHint)
    return splash


def run_trash_sender_test() -> None:
    from src.services.cleanup_service import (
        buscar_emails_por_remetente,
        mover_emails_para_lixeira,
    )
    from src.auth.oauth import get_gmail_service

    remetente = input("Remetente para buscar: ").strip()
    if not remetente:
        print("Nenhum remetente informado.")
        return

    print("Conectando ao Gmail...")
    service = get_gmail_service()

    print(f"Buscando e-mails com query: from:{remetente}")
    resultado = buscar_emails_por_remetente(service, remetente)
    total = resultado.total
    sem_anexo = len(resultado.emails_sem_anexo)
    com_anexo = len(resultado.emails_com_anexo)
    print(f"Quantidade encontrada: {total}")
    print(f"Sem anexo: {sem_anexo}")
    print(f"Com anexo protegidos: {com_anexo}")

    if sem_anexo == 0:
        print("Nenhum e-mail sem anexo para mover.")
        return

    confirmacao = input("Digite SIM para mover os e-mails sem anexo: ").strip()
    if confirmacao != "SIM":
        print("Operacao cancelada.")
        return

    movidos = mover_emails_para_lixeira(service, resultado.emails_sem_anexo)
    print(f"Concluido. {movidos} e-mail(s) movido(s) para a lixeira.")


if __name__ == "__main__":
    main()
