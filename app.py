#!/usr/bin/env python3
"""TG Dynamic Profile CLI.

Usage:
    python app.py login           # interactive login, creates the session file
    python app.py run             # run the update loop (foreground / systemd)
    python app.py menu            # interactive menu to edit config.json
"""
import argparse
import asyncio

from tgprofile.client import build_client
from tgprofile.config import load_config
from tgprofile.menu import menu
from tgprofile.runner import run_loop


def cmd_login(args):
    cfg = load_config(args.config)
    client = build_client(cfg)
    # Telethon's start() prompts for phone number + login code interactively.
    client.start()
    me = client.loop.run_until_complete(client.get_me())
    print(f"\n✅ Logged in as {me.first_name} (@{me.username})")
    print(f"   Session saved as: {cfg['session']}.session")
    client.disconnect()


def cmd_run(args):
    asyncio.run(run_loop(args.config))


def cmd_menu(args):
    menu(args.config)


def main():
    p = argparse.ArgumentParser(description="Telegram Dynamic Profile")
    p.add_argument("-c", "--config", default="config.json", help="config file path")
    sub = p.add_subparsers(dest="cmd", required=True)
    sub.add_parser("login", help="interactive login").set_defaults(func=cmd_login)
    sub.add_parser("run", help="run the update loop").set_defaults(func=cmd_run)
    sub.add_parser("menu", help="edit config interactively").set_defaults(func=cmd_menu)

    args = p.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
