import asyncio
import logging
import sys
from datetime import datetime, timedelta

from telethon import TelegramClient
from telethon.errors import SessionPasswordNeededError

from config import API_ID, API_HASH, BOT, MSG, SESSION_NAME, LOG_FILE, TZ, SIGN_TIME, REPLY_TIMEOUT

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.FileHandler(LOG_FILE, encoding="utf-8"), logging.StreamHandler(sys.stdout)],
)
log = logging.getLogger("ty-sign")


def _seconds_until_sign() -> float:
    h, m = map(int, SIGN_TIME.split(":"))
    now = datetime.now(TZ)
    nxt = now.replace(hour=h, minute=m, second=0, microsecond=0)
    if now >= nxt:
        nxt += timedelta(days=1)
    return (nxt - now).total_seconds()


async def _send_and_wait(client, target):
    sent = await client.send_message(target, MSG)
    log.info("Sign-in sent (message_id=%s)", sent.id)

    for _ in range(REPLY_TIMEOUT):
        await asyncio.sleep(1)
        async for msg in client.iter_messages(target, limit=5, min_id=sent.id):
            if msg.id > sent.id:
                log.info("Reply received: %s", msg.text or "(no text)")
                return
    log.info("Timeout waiting for reply")


async def main():
    client = TelegramClient(SESSION_NAME, API_ID, API_HASH)
    await client.connect()

    if not await client.is_user_authorized():
        log.info("Not authorized, starting QR login…")
        qr_login = await client.qr_login()
        log.info("Scan this QR code with Telegram mobile:")
        print()
        print(">>> ", qr_login.url)
        print()
        log.info("QR code expires at: %s", qr_login.expires.astimezone(TZ).strftime("%H:%M:%S"))
        try:
            await qr_login.wait()
        except SessionPasswordNeededError:
            pwd = input("2FA password: ").strip()
            await client.sign_in(password=pwd)

    target = await client.get_entity(BOT)
    log.info("Target: @%s | Sign time: %s | Timezone: %s", BOT, SIGN_TIME, TZ)

    await _send_and_wait(client, target)

    while True:
        wait = _seconds_until_sign()
        log.info("Next sign-in in %.0f seconds", wait)
        await asyncio.sleep(wait)
        await _send_and_wait(client, target)


if __name__ == "__main__":
    asyncio.run(main())
