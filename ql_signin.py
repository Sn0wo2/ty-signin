#!/usr/bin/env python3
"""
cron: 0 0 * * *
new Env("ty-sign")
"""
import asyncio
import os
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
os.chdir(SCRIPT_DIR)

from main import main

if __name__ == "__main__":
    asyncio.run(main())
