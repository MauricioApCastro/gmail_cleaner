from pathlib import Path

BASE_DIR = Path(__file__).resolve().parents[2]
CREDENTIALS_DIR = BASE_DIR / "credentials"
CLIENT_SECRET_FILE = CREDENTIALS_DIR / "client_secret.json"
TOKEN_FILE = CREDENTIALS_DIR / "token.json"
SRC_DIR = BASE_DIR / "src"
DATA_DIR = SRC_DIR / "data"
LOGS_DIR = SRC_DIR / "logs"
THEMES_DIR = SRC_DIR / "assets" / "themes"
LOGO_FILE = SRC_DIR / "assets" / "logo" / "logo.png"
ICON_FILE = SRC_DIR / "assets" / "logo" / "app_icon.ico"
CLEANUP_LOG_FILE = DATA_DIR / "history" / "cleanup_history.jsonl"

GMAIL_SCOPES = [
    "https://www.googleapis.com/auth/gmail.modify",
]
