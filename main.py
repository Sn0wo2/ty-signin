import asyncio
import logging
import sys
from datetime import datetime, timedelta

from telethon import TelegramClient, events
from telethon.errors import RPCError, SessionPasswordNeededError
from telethon.hints import Entity

from config import (
    API_ID, API_HASH, TARGETS, MSG, SESSION_NAME,
    LOG_FILE, TZ, SIGN_TIME, REPLY_TIMEOUT,
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.FileHandler(LOG_FILE, encoding="utf-8"), logging.StreamHandler(sys.stdout)],
)
log = logging.getLogger("nodeseek-api-signin")


def _seconds_until_sign() -> float:
    h, m = map(int, SIGN_TIME.split(":"))
    now = datetime.now(TZ)
    nxt = now.replace(hour=h, minute=m, second=0, microsecond=0)
    if now >= nxt:
        nxt += timedelta(days=1)
    return (nxt - now).total_seconds()


def _name(entity: Entity) -> str:
    return (
        f"@{entity.username}" if getattr(entity, "username", None)
        else getattr(entity, "title", None)
        or getattr(entity, "first_name", None)
        or str(getattr(entity, "id", entity))
    )


async def _sign(client: TelegramClient, entity: Entity) -> None:
    label = _name(entity)
    got_reply = asyncio.Event()

    async def _on_reply(event: events.NewMessage.Event) -> None:
        log.info("[%s] reply: %s", label, event.message.text or "(no text)")
        got_reply.set()

    client.add_event_handler(_on_reply, events.NewMessage(chats=entity, incoming=True))
    try:
        for attempt in range(3):
            try:
                sent = await client.send_message(entity, MSG)
                log.info("[%s] sent (id=%s)", label, sent.id)
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


async def main() -> None:
    if not TARGETS:
        log.error("No target configured. Set TARGET in your .env")
        return

    client = TelegramClient(SESSION_NAME, API_ID, API_HASH)
    await client.connect()
    await _login(client)

    entities = []
    for t in TARGETS:
        try:
            entities.append(await client.get_entity(t))
        except (RPCError, ConnectionError) as e:
            log.error("Cannot resolve %r: %s", t, e)
            log.error("Cannot resolve %r: %s", t, e)
    if not entities:
        log.error("No resolvable target, exiting")
        return

    log.info("Targets: %s | %s | %s", ", ".join(map(_name, entities)), SIGN_TIME, TZ)

    # Sign once on startup (catch-up if the daemon was down at SIGN_TIME), then daily.
    while True:
        for e in entities:
            await _sign(client, e)
        wait = _seconds_until_sign()
        log.info("Next sign-in in %.0f seconds", wait)
        await asyncio.sleep(wait)


if __name__ == "__main__":
    asyncio.run(main())
