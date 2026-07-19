#!/usr/bin/env python3
"""
cron: 0 0 * * *
new Env("ty-signin")
"""
import asyncio
import builtins
import os
from pathlib import Path
from typing import NoReturn

SCRIPT_DIR = Path(__file__).resolve().parent
os.chdir(SCRIPT_DIR)

from main import RunResult, main


def _notify(result: RunResult) -> None:
    ql_api = getattr(builtins, "QLAPI", None)
    if ql_api is None:
        return

    status = "[OK]" if result.success else "[FAIL]"
    content = result.details or result.summary
    try:
        ql_api.systemNotify({
            "title": f"{status} ty-signin {result.summary}",
            "content": content,
        })
    except Exception as error:
        print(f"QLAPI notification failed: {error}")


def run(*, login_only: bool = False) -> NoReturn:
    try:
        result = asyncio.run(main(login_only=login_only))
    except Exception as error:
        result = RunResult(False, "Unexpected error", str(error))
        print(f"ty-signin failed: {error}")
    _notify(result)
    raise SystemExit(result.exit_code)


if __name__ == "__main__":
    run()
