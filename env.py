import os
import json
import sys
import argparse
from pathlib import Path
from typing import TypeAlias, TypedDict, cast
from zoneinfo import ZoneInfo
from dotenv import load_dotenv

load_dotenv()

DATA_DIR = Path(os.getenv("DATA_DIR", ".data"))
SESSION_DIR = DATA_DIR / "session"
LOGS_DIR = DATA_DIR / "logs"

SESSION_DIR.mkdir(parents=True, exist_ok=True)
LOGS_DIR.mkdir(parents=True, exist_ok=True)

API_ID = int(os.getenv("API_ID", "0"))
API_HASH = os.getenv("API_HASH", "")
TZ = ZoneInfo(os.getenv("TIMEZONE", "Asia/Shanghai"))
REPLY_TIMEOUT = int(os.getenv("REPLY_TIMEOUT", "15"))
LOG_FILE = os.getenv("LOG_FILE", str(LOGS_DIR / "signin.log"))

TaskTarget: TypeAlias = str | int


class TaskConfig(TypedDict):
    session: str
    session_path: str
    target: TaskTarget
    parsed_target: TaskTarget
    time: str
    message: str


def _parse_target(raw: str | int) -> int | str:
    """Normalize one target into something get_entity() accepts.

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

def parse_time(raw: str) -> tuple[int, int]:
    try:
        hour, minute = map(int, raw.strip().split(":"))
    except ValueError as exc:
        raise ValueError("SIGNIN_CONFIG task time must use HH:MM format") from exc

    if not 0 <= hour <= 23 or not 0 <= minute <= 59:
        raise ValueError("SIGNIN_CONFIG task time must be a valid 24-hour time")

    return hour, minute


def _required_value(item: dict[str, object], idx: int, key: str) -> object:
    if key not in item:
        raise ValueError(f"Task index {idx} in SIGNIN_CONFIG is missing required field '{key}'")
    return item[key]


def _required_str(item: dict[str, object], idx: int, key: str) -> str:
    value = _required_value(item, idx, key)
    if not isinstance(value, str):
        raise ValueError(f"Task index {idx} in SIGNIN_CONFIG field '{key}' must be a string")
    return value


def _required_target(item: dict[str, object], idx: int) -> TaskTarget:
    value = _required_value(item, idx, "target")
    if not isinstance(value, (str, int)):
        raise ValueError(f"Task index {idx} in SIGNIN_CONFIG field 'target' must be a string or integer")
    return value


def load_tasks() -> list[TaskConfig]:
    raw_config = os.getenv("SIGNIN_CONFIG", "[]")
    if not raw_config.strip():
        return []
    
    try:
        tasks: object = json.loads(raw_config)
    except json.JSONDecodeError as e:
        raise ValueError(f"SIGNIN_CONFIG is not a valid JSON: {e}") from e

    if not isinstance(tasks, list):
        raise ValueError("SIGNIN_CONFIG must be a JSON list of tasks")

    normalized_tasks: list[TaskConfig] = []
    for idx, raw_item in enumerate(cast(list[object], tasks)):
        if not isinstance(raw_item, dict):
            raise ValueError(f"Task index {idx} in SIGNIN_CONFIG must be a JSON object")
        item = cast(dict[str, object], raw_item)

        session = _required_str(item, idx, "session")
        target = _required_target(item, idx)
        task_time = _required_str(item, idx, "time")
        message = _required_str(item, idx, "message")

        _ = parse_time(task_time)

        # Strip path traversal elements to keep it in SESSION_DIR safely
        session_file = Path(session).name
        session_path = SESSION_DIR / session_file
        
        normalized_tasks.append({
            "session": session,
            "session_path": str(session_path),
            "target": target,
            "parsed_target": _parse_target(target),
            "time": task_time,
            "message": message
        })
        
    return normalized_tasks

try:
    TASKS = load_tasks()
except ValueError as e:
    sys.stderr.write(f"Configuration Error: {e}\n")
    sys.exit(1)

def parse_args():
    parser = argparse.ArgumentParser(description="Telegram Auto Sign-in parameter parsing")
    parser.add_argument("--login-only", action="store_true", help="Login all configured sessions and exit")
    parser.add_argument("--session-path", type=str, help="Telegram session path to run for a specific task")
    parser.add_argument("--target", type=str, help="Telegram target entity (numeric ID or username) for a specific task")
    parser.add_argument("--message", type=str, help="Message to send for a specific task")
    return parser.parse_args()
