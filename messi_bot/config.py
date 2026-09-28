import os
from pathlib import Path
from zoneinfo import ZoneInfo

from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent
load_dotenv(BASE_DIR / ".env")

BOT_TOKEN = os.environ["BOT_TOKEN"]

OWNER_ID = int(os.getenv("OWNER_ID", "1270318984"))
GIRLFRIEND_ID = int(os.getenv("GIRLFRIEND_ID", "5197933099"))
OWNER_NAME = os.getenv("OWNER_NAME", "папа")
GIRLFRIEND_NAME = os.getenv("GIRLFRIEND_NAME", "мама")

# Кто есть кто: id -> как Месси к нему обращается
FAMILY = {OWNER_ID: OWNER_NAME, GIRLFRIEND_ID: GIRLFRIEND_NAME}

TIMEZONE = ZoneInfo(os.getenv("TIMEZONE", "Europe/Moscow"))

CLAUDE_MODEL = os.getenv("CLAUDE_MODEL", "claude-opus-5")
CLAUDE_EFFORT = os.getenv("CLAUDE_EFFORT", "medium")

PROACTIVE_MESSAGES = os.getenv("PROACTIVE_MESSAGES", "1") == "1"
PROACTIVE_MAX_PER_DAY = int(os.getenv("PROACTIVE_MAX_PER_DAY", "3"))

DB_PATH = os.getenv("DB_PATH", str(BASE_DIR / "messi.db"))

# Сколько последних сообщений переписки Месси «держит в голове»
HISTORY_LIMIT = 40


def other_member(user_id: int) -> int:
    return GIRLFRIEND_ID if user_id == OWNER_ID else OWNER_ID
