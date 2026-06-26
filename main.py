import asyncio
import logging
import sys
from collections import defaultdict
from pathlib import Path
from typing import Any, cast

from telethon import TelegramClient, events
from telethon.errors import RPCError, SessionPasswordNeededError
from telethon.hints import Entity

from env import (
    API_ID, API_HASH, TZ, REPLY_TIMEOUT, LOG_FILE, TASKS, TaskConfig, parse_args, _parse_target
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.FileHandler(LOG_FILE, encoding="utf-8"), logging.StreamHandler(sys.stdout)],
)
log = logging.getLogger("nodeseek-api-signin")


def _name(entity: Any) -> str:
    if isinstance(entity, str):
        return entity
    username = getattr(entity, "username", None)
    if username:
        return f"@{username}"
    title = getattr(entity, "title", None)
    if isinstance(title, str) and title:
        return title
    first_name = getattr(entity, "first_name", None)
    if first_name:
        return first_name
    return str(getattr(entity, "id", entity))


async def _signin(client: TelegramClient, entity: Entity, message: str) -> None:
    label = _name(entity)
    got_reply = asyncio.Event()

    async def _on_reply(event: events.NewMessage.Event) -> None:
        log.info("[%s] reply: %s", label, event.message.text or "(no text)")
        got_reply.set()

    client.add_event_handler(_on_reply, events.NewMessage(chats=entity, incoming=True))
    try:
        for attempt in range(3):
            try:
                sent = await client.send_message(entity, message)
                log.info("[%s] sent (id=%s): %r", label, sent.id, message)
                try:
                    await asyncio.wait_for(got_reply.wait(), timeout=REPLY_TIMEOUT)
                except asyncio.TimeoutError:
                    log.info("[%s] no reply (timeout)", label)
                return
            except (RPCError, ConnectionError) as e:
                if attempt < 2:
                    delay = 2 ** attempt
                    log.warning("[%s] attempt %d failed: %s, retrying in %ds", label, attempt + 1, e, delay)
                    await asyncio.sleep(delay)
                else:
                    log.error("[%s] failed after 3 attempts: %s", label, e)
    finally:
        client.remove_event_handler(_on_reply)


async def _login(client: TelegramClient) -> None:
    if await client.is_user_authorized():
        return
    log.info("Not authorized, starting QR login…")
    qr = await client.qr_login()
    print(f"\nScan with Telegram:\n>>>  {qr.url}\n")
    log.info("QR expires at %s", qr.expires.astimezone(TZ).strftime("%H:%M:%S"))
    try:
        await qr.wait()
    except SessionPasswordNeededError:
        await client.sign_in(password=input("2FA password: ").strip())


async def _login_only(tasks: list[TaskConfig]) -> None:
    unique_sessions = {t.session_path: t.session for t in tasks}
    log.info("Starting login for %d sessions...", len(unique_sessions))
    for session_path, session_name in unique_sessions.items():
        log.info("Logging into session: %s (%s)", session_name, session_path)
        client = TelegramClient(session_path, API_ID, API_HASH)
        await client.connect()
        try:
            await _login(client)
            log.info("Successfully authorized session: %s", session_name)
        finally:
            await client.disconnect()
    log.info("All sessions processed.")


async def _run_session_group(
    session_path: str,
    group_tasks: list[TaskConfig],
    is_single_task: bool,
) -> None:
    session_name = group_tasks[0].session
    if not is_single_task:
        log.info("Processing session: %s (%s) with %d tasks", session_name, session_path, len(group_tasks))

    client = TelegramClient(session_path, API_ID, API_HASH)
    await client.connect()
    try:
        await _login(client)
        for task in group_tasks:
            try:
                entity = await client.get_entity(task.parsed_target)
            except (RPCError, ConnectionError) as e:
                if is_single_task:
                    log.error("Cannot resolve %r: %s", task.parsed_target, e)
                else:
                    log.error("[%s] Cannot resolve %r: %s", session_name, task.parsed_target, e)
                continue
            entity = cast(Entity, entity)
            await _signin(client, entity, task.message)
    finally:
        await client.disconnect()


async def main() -> None:
    if not API_ID or not API_HASH:
        log.error("Missing API_ID or API_HASH. Set them in your environment")
        return

    args = parse_args()

    if args.login_only:
        if not TASKS:
            log.error("No tasks found in SIGNIN_CONFIG. Please configure it first")
            return
        return await _login_only(TASKS)

    if args.session_path and args.target and args.message is not None:
        session_path = args.session_path
        log.info("Running single task | session: %s | target: %s | message: %r", session_path, args.target, args.message)
        session_name = Path(session_path).stem
        task = TaskConfig(session=session_name, target=_parse_target(args.target), time="00:00", message=args.message)
        await _run_session_group(session_path, [task], is_single_task=True)
        return

    if not TASKS:
        log.error("No tasks configured in SIGNIN_CONFIG")
        return

    session_groups: dict[str, list[TaskConfig]] = defaultdict(list)
    for task in TASKS:
        session_groups[task.session_path].append(task)
    log.info("Running all tasks in batch mode...")
    for session_path, group_tasks in session_groups.items():
        await _run_session_group(session_path, group_tasks, is_single_task=False)
    log.info("Batch run completed")


if __name__ == "__main__":
    asyncio.run(main())
