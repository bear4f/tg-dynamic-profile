#!/usr/bin/env python3
"""TG Dynamic Profile CLI.

用法:
    python app.py setup           # 一键向导：填凭证 -> 登录 -> 选模式
    python app.py login           # 仅登录（生成 session 文件）
    python app.py run             # 启动更新循环（运行时会自动感知 config.json 变化）
    python app.py menu            # 交互菜单：改配置，几秒内自动生效，不用重启
"""
import argparse
import asyncio
import json
import os
from zoneinfo import ZoneInfo

from rich.prompt import Confirm, Prompt

from tgprofile.client import build_client
from tgprofile.config import load_config, save_config
from tgprofile.menu import menu
from tgprofile.providers import REGISTRY
from tgprofile.runner import run_loop
from tgprofile.ui import banner, console, err, ok, section

HERE = os.path.dirname(os.path.abspath(__file__))


def _login(cfg):
    client = build_client(cfg)
    client.start()  # Telethon prompts for phone number + login code
    me = client.loop.run_until_complete(client.get_me())
    client.disconnect()
    return me


def _ask_api_id():
    while True:
        raw = Prompt.ask("api_id").strip()
        if raw.isdigit() and int(raw) > 0:
            return int(raw)
        err("api_id 必须是正整数")


def _ask_api_hash():
    while True:
        raw = Prompt.ask("api_hash").strip()
        if raw:
            return raw
        err("api_hash 不能为空")


def _ask_mode(default):
    modes = sorted(REGISTRY)
    console.print("可用模式: " + ", ".join(modes))
    while True:
        m = Prompt.ask("模式", default=default).strip()
        if m in REGISTRY:
            return m
        err(f"未知模式 '{m}'，请从上面列表中选择")


def _ask_timezone(default):
    while True:
        tz = Prompt.ask("时区（如 Asia/Shanghai）", default=default).strip()
        try:
            ZoneInfo(tz)
            return tz
        except Exception:
            err(f"无效时区 '{tz}'，示例: Asia/Shanghai / Europe/London / UTC")


def cmd_setup(args):
    """一键式部署向导：填凭证 -> 登录 -> 选模式，全程中文引导。"""
    banner("Telegram Dynamic Profile · 部署向导", "Debian/Ubuntu VPS 一步到位")
    path = args.config
    make_config = True
    if os.path.exists(path):
        make_config = Confirm.ask(f"{path} 已存在，是否覆盖重新配置?", default=False)

    if make_config:
        with open(os.path.join(HERE, "config.example.json"), encoding="utf-8") as f:
            cfg = json.load(f)

        section("1) Telegram API 凭证（前往 https://my.telegram.org 获取）")
        cfg["api_id"] = _ask_api_id()
        cfg["api_hash"] = _ask_api_hash()

        section("2) 昵称设置")
        cfg["prefix"] = Prompt.ask("前缀（名字主体）", default=cfg["prefix"]).strip() or cfg["prefix"]
        cfg["mode"] = _ask_mode(cfg["mode"])
        cfg["timezone"] = _ask_timezone(cfg["timezone"])

        save_config(path, cfg)
        ok(f"已写入 {path}")

    section("3) 登录 Telegram")
    me = _login(load_config(path))
    ok(f"登录成功: {me.first_name} (@{me.username})")

    section("完成")
    console.print("前台运行:  [bold]python app.py run[/bold]")
    console.print("改配置:    另开终端跑 [bold]python app.py menu[/bold]（改模式/前缀/参数，带预览），"
                  "保存后几秒内自动生效，不用重启")
    console.print("常驻服务:  见 README『部署为 systemd 服务』")


def cmd_login(args):
    me = _login(load_config(args.config))
    ok(f"登录成功: {me.first_name} (@{me.username})")


def cmd_run(args):
    asyncio.run(run_loop(args.config))


def cmd_menu(args):
    menu(args.config)


def main():
    p = argparse.ArgumentParser(description="Telegram 动态昵称系统")
    p.add_argument("-c", "--config", default="config.json", help="配置文件路径")
    sub = p.add_subparsers(dest="cmd", required=True)
    sub.add_parser("setup", help="一键部署向导（凭证/登录/模式）").set_defaults(func=cmd_setup)
    sub.add_parser("login", help="仅登录 Telegram（生成 session）").set_defaults(func=cmd_login)
    sub.add_parser("run", help="启动更新循环（自动感知配置变化）").set_defaults(func=cmd_run)
    sub.add_parser("menu", help="交互菜单，修改配置").set_defaults(func=cmd_menu)

    args = p.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
