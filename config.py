import os
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
if not BOT_TOKEN:
    raise RuntimeError("BOT_TOKEN mancante: controlla il file .env")

DB_PATH = os.getenv("DB_PATH", "./data/prices.db")
CHECK_INTERVAL_HOURS = int(os.getenv("CHECK_INTERVAL_HOURS", "6"))
HISTORY_RETENTION_DAYS = int(os.getenv("HISTORY_RETENTION_DAYS", "365"))
# cap per chat: senza, un singolo utente può gonfiare il DB e stallare il job per tutti
MAX_TRACKED_PER_CHAT = int(os.getenv("MAX_TRACKED_PER_CHAT", "25"))

PROXY_URL = os.getenv("PROXY_URL", "192.168.1.234")
PROXY_PORT = int(os.getenv("PROXY_PORT", "8191"))
PROXY_TIMEOUT = int(os.getenv("PROXY_TIMEOUT", "60"))

AUTHORIZED_USER_IDS = os.getenv("AUTHORIZED_USER_IDS", "")
AUTH_USER_IDS = {
    int(user_id.strip())
    for user_id in AUTHORIZED_USER_IDS.split(",")
    if user_id.strip()
}
