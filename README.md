# ty-sign

Telegram sign-in automation built on Telethon.

## QingLong

Add the repository as a QingLong subscription:

```text
Name: ty-sign
Repository: https://github.com/Sn0wo2/ty-sign.git
Branch: main
Schedule: 0 0 * * *
File suffix: py
Whitelist: (leave empty)
Dependency file: leave empty
```

### Install dependencies

QingLong does not install dependencies from Poetry files. Add these versions under **Dependency Management -> Python3**:

```text
telethon==1.44.0
pydantic==2.13.4
python-dotenv==1.2.2
tzdata==2026.3
```

### Configure the environment

Add these variables in QingLong:

```text
TY_SIGNIN_API_ID=YOUR_TELEGRAM_API_ID
TY_SIGNIN_API_HASH=YOUR_TELEGRAM_API_HASH
TY_SIGNIN_CONFIG=<JSON array — see below>
TY_SIGNIN_DATA_DIR=/ql/data/ty-sign-data
TY_SIGNIN_TIMEZONE=Asia/Singapore
TY_SIGNIN_REPLY_TIMEOUT=15
```

`TY_SIGNIN_CONFIG` is a JSON array. Each item requires `session`, `target`, and `message`:

```json
[
  {
    "session": "ty_signin",
    "target": "YOUR_BOT",
    "message": "YOUR_SIGNIN_MESSAGE"
  },
  {
    "session": "ty_signin",
    "target": "YOUR_GROUP_OR_CHANNEL",
    "message": "YOUR_SIGNIN_MESSAGE"
  }
]
```

Optional variables:

```text
TY_SIGNIN_LOG_FILE=/ql/data/ty-signin-data/logs/ty-signin.log
# Set temporarily when the Telegram account has 2FA enabled.
TY_SIGNIN_2FA_PASSWORD=YOUR_TELEGRAM_2FA_PASSWORD
```
