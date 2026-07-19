import argparse
import json
import os
import sys
from datetime import time
from pathlib import Path
from zoneinfo import ZoneInfo

from dotenv import load_dotenv
from pydantic import BaseModel, model_validator

load_dotenv()

DATA_DIR = Path(os.getenv("DATA_DIR", ".data"))
API_ID = int(os.getenv("API_ID", "0"))
API_HASH = os.getenv("API_HASH", "")
TZ = ZoneInfo(os.getenv("TIMEZONE", "Asia/Shanghai"))
REPLY_TIMEOUT = int(os.getenv("REPLY_TIMEOUT", "15"))

SESSION_DIR = DATA_DIR / "session"
LOGS_DIR = DATA_DIR / "logs"
LOG_FILE = os.getenv("LOG_FILE", str(LOGS_DIR / "ty-signin.log"))

SESSION_DIR.mkdir(parents=True, exist_ok=True)
LOGS_DIR.mkdir(parents=True, exist_ok=True)


def _parse_target(raw: str | int) -> str | int:
    """
    Works for users / groups / channels / bots alike:
      "@name" / "name" / "t.me/name"  -> username
      "123" / "-1001234567890"        -> peer id
    """
    if isinstance(raw, int):
        return raw
    t = str(raw).strip()
    for p in ("https://t.me/", "http://t.me/", "t.me/"):
        if t.lower().startswith(p):
            t = t[len(p):]
    t = t.lstrip("@")
    return int(t) if t.lstrip("-").isdigit() else t


class TaskConfig(BaseModel):
    session: str
    target: str | int
    time: time
    message: str
    session_path: str = ""
    parsed_target: str | int = ""

    @model_validator(mode="after")
    def compute_derived_fields(self) -> "TaskConfig":
        self.session_path = str(SESSION_DIR / Path(self.session).name)
        self.parsed_target = _parse_target(self.target)
        return self

def load_tasks() -> list[TaskConfig]:
    raw_config = os.getenv("SIGNIN_CONFIG", "[]")
    if not raw_config.strip():
        raise ValueError("SIGNIN_CONFIG environment variable must not be empty")

    try:
        tasks = json.loads(raw_config)
    except json.JSONDecodeError as e:
        raise ValueError(f"SIGNIN_CONFIG is not a valid JSON: {e}") from e

    if not isinstance(tasks, list):
        raise ValueError("SIGNIN_CONFIG must be a JSON list of tasks")

    return [TaskConfig.model_validate(item) for item in tasks]


try:
    TASKS = load_tasks()
except ValueError as e:
    sys.stderr.write(f"Configuration Error: {e}\n")
    sys.exit(1)

def parse_args():
    parser = argparse.ArgumentParser(description="Telegram Auto Sign-in parameter parsing")
    parser.add_argument("--login-only", action="store_true", help="Login all configured sessions and exit")
    parser.add_argument("--session-path", type=str, help="Telegram session path to run for a specific task")
    parser.add_argument("--target", type=str,
                        help="Telegram target entity (numeric ID or username) for a specific task")
    parser.add_argument("--message", type=str, help="Message to send for a specific task")
    return parser.parse_args()
