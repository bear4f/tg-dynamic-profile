#!/usr/bin/env python3
"""TG Dynamic Profile CLI.

Usage:
    python app.py setup           # guided wizard: creds -> login -> mode (one-shot)
    python app.py login           # interactive login only (creates session file)
    python app.py run             # run the update loop + emoji control panel
    python app.py menu            # local menu to edit config.json
"""
import argparse
import asyncio
import json
import os

from tgprofile.client import build_client
from tgprofile.config import load_config, save_config
from tgprofile.menu import menu
from tgprofile.providers import REGISTRY
from tgprofile.runner import run_loop

HERE = os.path.dirname(os.path.abspath(__file__))


def _login(cfg):
    client = build_client(cfg)
    client.start()  # Telethon prompts for phone number + login code
    me = client.loop.run_until_complete(client.get_me())
    client.disconnect()
    return me


def cmd_setup(args):
    """One-shot guided deployment wizard."""
    path = args.config
    make_config = True
    if os.path.exists(path):
        ans = input(f"{path} 已存在，覆盖重新配置? [y/N] ").strip().lower()
        make_config = ans == "y"

    if make_config:
        with open(os.path.join(HERE, "config.example.json"), encoding="utf-8") as f:
            cfg = json.load(f)
        print("\n=== 1) Telegram API 凭证 (https://my.telegram.org) ===")
        cfg["api_id"] = int(input("api_id: ").strip())
        cfg["api_hash"] = input("api_hash: ").strip()

        print("\n=== 2) 昵称设置 ===")
        cfg["prefix"] = input(f"前缀(名字主体) [{cfg['prefix']}]: ").strip() or cfg["prefix"]
        print("可用模式:", ", ".join(sorted(REGISTRY)))
        m = input(f"模式 [{cfg['mode']}]: ").strip()
        if m and m in REGISTRY:
            cfg["mode"] = m
        cfg["timezone"] = input(f"时区 [{cfg['timezone']}]: ").strip() or cfg["timezone"]

        save_config(path, cfg)
        print(f"✅ 已写入 {path}")

    print("\n=== 3) 登录 Telegram ===")
    me = _login(load_config(path))
    print(f"✅ 登录成功: {me.first_name} (@{me.username})")

    print("\n=== 完成 ===")
    print("前台运行:  python app.py run")
    print("控制面板:  运行后在 Telegram 收藏夹发送 ⚙️")
    print("常驻服务:  见 README『部署为 systemd 服务』")


def cmd_login(args):
    me = _login(load_config(args.config))
    print(f"\n✅ Logged in as {me.first_name} (@{me.username})")


def cmd_run(args):
    asyncio.run(run_loop(args.config))


def cmd_menu(args):
    menu(args.config)


def main():
    p = argparse.ArgumentParser(description="Telegram Dynamic Profile")
    p.add_argument("-c", "--config", default="config.json", help="config file path")
    sub = p.add_subparsers(dest="cmd", required=True)
    sub.add_parser("setup", help="guided setup wizard").set_defaults(func=cmd_setup)
    sub.add_parser("login", help="interactive login").set_defaults(func=cmd_login)
    sub.add_parser("run", help="run the update loop + control panel").set_defaults(func=cmd_run)
    sub.add_parser("menu", help="edit config interactively").set_defaults(func=cmd_menu)

    args = p.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
