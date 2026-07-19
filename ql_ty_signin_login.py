#!/usr/bin/env python3
"""
cron: 0 0 1 1 *
new Env("ty-signin-login")
"""
from ql_ty_signin import run

if __name__ == "__main__":
    run(login_only=True)
