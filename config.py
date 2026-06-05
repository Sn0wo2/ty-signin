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


def _parse_target(raw: str) -> int | str:
    """Normalize one target into something get_entity() accepts.

    Works for users / groups / channels / bots alike:
      "@name" / "name" / "t.me/name"  -> username
      "123" / "-1001234567890"        -> peer id
    """
    t = raw.strip()
    for p in ("https://t.me/", "http://t.me/", "t.me/"):
        if t.lower().startswith(p):
            t = t[len(p):]
    t = t.lstrip("@")
    return int(t) if t.lstrip("-").isdigit() else t


API_ID = int(os.getenv("API_ID", "0"))
API_HASH = os.getenv("API_HASH", "")
TARGETS = [_parse_target(x) for x in os.getenv("TARGET", "").split(",") if x.strip()]
MSG = os.getenv("SIGN_MESSAGE", "📅 每日签到")
SESSION_NAME = os.getenv("SESSION_NAME", str(SESSION_DIR / "nodeseek_api_signin"))
LOG_FILE = os.getenv("LOG_FILE", str(LOGS_DIR / "sign.log"))
TZ = ZoneInfo(os.getenv("TIMEZONE", "Asia/Shanghai"))
SIGN_TIME = os.getenv("SIGN_TIME", "00:00")
REPLY_TIMEOUT = int(os.getenv("REPLY_TIMEOUT", "15"))
