import logging
import subprocess
import sys
import time
from datetime import datetime, timedelta
from pathlib import Path

from env import TZ, TASKS, TaskConfig

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)
log = logging.getLogger("nodeseek-api-signin-scheduler")


def _next_run(now: datetime, hour: int, minute: int) -> datetime:
    nxt = now.replace(hour=hour, minute=minute, second=0, microsecond=0)
    if now >= nxt:
        nxt += timedelta(days=1)
    return nxt


def _run_task(task: TaskConfig) -> int:
    script = Path(__file__).with_name("main.py")
    args = [
        sys.executable,
        str(script),
        "--session-path", task.session_path,
        "--target", str(task.target),
        "--message", task.message
    ]
    return subprocess.run(args, check=False).returncode


def main() -> None:
    if not TASKS:
        log.error("No tasks configured in SIGNIN_CONFIG. Scheduler cannot start.")
        return

    log.info("Scheduler started | timezone=%s | total_tasks=%d", TZ, len(TASKS))
    for t in TASKS:
        log.info("  Task: session=%s, target=%s, time=%s, message=%r",
                 t.session, t.target, t.time, t.message)

    while True:
        now = datetime.now(TZ)

        task_runs: list[tuple[TaskConfig, datetime]] = []
        for task in TASKS:
            nxt = _next_run(now, task.time.hour, task.time.minute)
            task_runs.append((task, nxt))

        task_runs.sort(key=lambda x: x[1])
        earliest_task, earliest_time = task_runs[0]

        wait = max((earliest_time - now).total_seconds(), 0)
        log.info("Next task [%s -> %s] scheduled at %s (in %.0f seconds)",
                 earliest_task.session, earliest_task.target,
                 earliest_time.strftime("%Y-%m-%d %H:%M:%S %Z"), wait)

        if wait > 0:
            time.sleep(wait)

        now_after = datetime.now(TZ)
        # Give a 5-second buffer window to prevent missing any task due to OS sleep/scheduling drift
        due_tasks: list[TaskConfig] = []
        for task, nxt in task_runs:
            if nxt <= now_after + timedelta(seconds=5):
                due_tasks.append(task)

        log.info("Woke up. Due tasks to execute: %d", len(due_tasks))
        # Execute due tasks sequentially to prevent SQLite lock errors on shared session files
        for task in due_tasks:
            log.info("Executing task: %s -> %s | msg: %r", task.session, task.target, task.message)
            code = _run_task(task)
            if code:
                log.error("Task failed (exit code %s): %s -> %s", code, task.session, task.target)
            else:
                log.info("Task completed successfully: %s -> %s", task.session, task.target)

        # Small delay before next tick to avoid tight spin-loop
        time.sleep(2)


if __name__ == "__main__":
    main()
