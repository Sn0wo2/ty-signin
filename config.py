import os
from pathlib import Path
from zoneinfo import ZoneInfo
from dotenv import load_dotenv

load_dotenv()

DATA_DIR = Path(".data")
SESSION_DIR = DATA_DIR / "session"
LOGS_DIR = DATA_DIR / "logs"
SESSION_DIR.mkdir(parents=True, exist_ok=True)
LOGS_DIR.mkdir(parents=True, exist_ok=True)

API_ID = int(os.getenv("API_ID", "0"))
API_HASH = os.getenv("API_HASH", "")
BOT = os.getenv("TARGET_BOT", "freexzteam_bot")
MSG = os.getenv("SIGN_MESSAGE", "📅 每日签到")
SESSION_NAME = os.getenv("SESSION_NAME", str(SESSION_DIR / "ty_sign"))
LOG_FILE = os.getenv("LOG_FILE", str(LOGS_DIR / "sign.log"))
TZ = ZoneInfo(os.getenv("TIMEZONE", "Asia/Shanghai"))
SIGN_TIME = os.getenv("SIGN_TIME", "00:00")
REPLY_TIMEOUT = int(os.getenv("REPLY_TIMEOUT", "15"))
