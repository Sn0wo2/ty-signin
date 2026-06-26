# ty-sign

Telegram auto sign-in tool based on Telethon. It reads `SIGNIN_CONFIG`, logs in with one or more Telegram sessions, and
sends configured sign-in messages to bots, users, groups, or channels.

## QingLong panel deployment

QingLong should run this repo as a one-shot cron script. Do not run `scheduler.py` in QingLong, because that script is a
forever-running Docker scheduler.

### 1. Subscribe to the GitHub repo

In QingLong, add a subscription:

```text
Name: ty-sign
Repo URL: https://github.com/Sn0wo2/ty-sign.git
Branch: main
Cron: 0 0 * * *
Whitelist: ql_signin.py|main.py|env.py|pyproject.toml|poetry.lock
Dependency file: leave empty
```

`Cron` here controls how often QingLong pulls updates from GitHub. The actual sign-in task cron is declared in
`ql_signin.py` as `cron: 0 0 * * *`; change that line if you want QingLong to create the task at a different time.

The whitelist keeps QingLong from treating helper, Docker, or test files as task scripts while still pulling the modules
that `ql_signin.py` imports and the Poetry dependency files.

After the subscription syncs, the scripts are usually placed under a path like:

```text
/ql/data/scripts/ty-sign
```

### 2. Install Python dependencies

This project uses Poetry. Install Poetry once in the QingLong container, then install the project dependencies from
`pyproject.toml`:

```bash
pip3 install poetry
cd /ql/data/scripts/ty-sign
poetry config virtualenvs.create false
poetry install --only main --no-root
```

`virtualenvs.create false` installs dependencies into QingLong's Python environment, so the auto-created
`python3 ql_signin.py` task can import Telethon normally.

If you prefer QingLong's dependency manager, install the packages from `pyproject.toml` manually:

```text
telethon
python-dotenv
tzdata
```

### 3. Add QingLong environment variables

Add these variables in QingLong's environment variable page:

```text
API_ID=your_api_id
API_HASH=your_api_hash
DATA_DIR=/ql/data/ty-sign
TIMEZONE=Asia/Shanghai
REPLY_TIMEOUT=15
```

Then add `SIGNIN_CONFIG` as a JSON list. Each task must include `session`, `target`, `time`, and `message`:

```json
[
  {
    "session": "ty_signin",
    "target": "freexzteam_bot",
    "time": "00:00",
    "message": "📅 每日签到"
  },
  {
    "session": "ty_signin",
    "target": "free_yaya_bot",
    "time": "00:00",
    "message": "✅ 签到"
  }
]
```

`DATA_DIR` is recommended for QingLong so Telegram session files and logs are stored outside the subscribed git
worktree. Sessions are saved under `${DATA_DIR}/session`.

### 4. First-time Telegram login

Before the scheduled sign-in can run, each configured `session` must be authorized once.

Create a temporary QingLong task or manually run this command in the subscribed repo directory:

```bash
python3 ql_signin.py --login-only
```

Open the task log, scan the printed Telegram QR login URL/code, and wait until the script reports the session is
authorized. If the Telegram account has 2FA enabled, run the command from an interactive shell because it needs password
input.

### 5. Create the scheduled QingLong task

Create a QingLong task with the command:

```bash
python3 ql_signin.py
```

Set the cron time in QingLong. `ql_signin.py` runs all configured tasks once and exits. The `time` field in
`SIGNIN_CONFIG` is still validated and used by Docker `scheduler.py`, but QingLong's own cron controls when
`ql_signin.py` runs.

## Docker deployment

Docker uses the built-in forever scheduler:

```bash
cp .env.example .env
# edit .env
cd docker
docker compose up -d
```

The Docker container starts `python scheduler.py`, which reads each task's `time` and waits for the next due run.

## Configuration

Required variables:

```text
API_ID      Telegram API ID
API_HASH    Telegram API hash
SIGNIN_CONFIG JSON list of sign-in tasks
```

Optional variables:

```text
DATA_DIR       Data directory for sessions and default logs. Defaults to .data
LOG_FILE       Explicit log file path. Defaults to ${DATA_DIR}/logs/signin.log
TIMEZONE       Timezone for scheduler and QR expiry logs. Defaults to Asia/Shanghai
REPLY_TIMEOUT  Seconds to wait for a bot reply. Defaults to 15
```

Task fields in `SIGNIN_CONFIG`:

```text
session  Required. Telegram session name. Same session can be reused by multiple tasks.
target   Required. Bot/user/channel/group username, numeric ID, or t.me link.
time     Required. HH:MM 24-hour time. Used by Docker scheduler; validated everywhere.
message  Required. Message sent to the target.
```

## Commands

```bash
python3 ql_signin.py              # QingLong one-shot run, executes all tasks once
python3 ql_signin.py --login-only # Authorize all configured sessions and exit
python3 main.py                 # Same one-shot behavior as ql_signin.py, without chdir wrapper
python3 scheduler.py            # Docker/local forever scheduler
```
