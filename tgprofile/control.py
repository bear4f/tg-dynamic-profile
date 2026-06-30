"""Emoji-summoned live control panel.

Send the trigger emoji (default ⚙️) to your Telegram Saved Messages and the
running userbot edits it into a control panel. Then send dot-commands in the
same chat to change settings live, e.g. `.mode weather`, `.prefix Bob`,
`.interval 120`, `.off`.
"""
import json
import logging

from telethon import events

from .providers import REGISTRY

log = logging.getLogger("tgprofile")


def _status(state):
    c = state.cfg
    flag = "⏸ 已暂停" if state.paused else "▶ 运行中"
    return (f"{flag} | mode=<b>{c['mode']}</b> "
            f"prefix=<b>{c.get('prefix', '')}</b> "
            f"sep='{c.get('separator', ' ')}' "
            f"interval={c.get('update_interval', 60)}s "
            f"tz={c.get('timezone', 'UTC')}")


def _panel(state, cprefix):
    return (
        "⚙️ <b>Dynamic Profile 控制面板</b>\n"
        f"{_status(state)}\n"
        "──────────────\n"
        "在本对话直接发送命令修改：\n"
        f"• <code>{cprefix}mode &lt;名称&gt;</code> 切换模式\n"
        f"• <code>{cprefix}prefix &lt;文本&gt;</code> 改前缀\n"
        f"• <code>{cprefix}interval &lt;秒&gt;</code> 改刷新间隔\n"
        f"• <code>{cprefix}sep &lt;字符&gt;</code> 改分隔符\n"
        f"• <code>{cprefix}tz &lt;时区&gt;</code> 改时区\n"
        f"• <code>{cprefix}off</code> / <code>{cprefix}on</code> 暂停/恢复\n"
        f"• <code>{cprefix}status</code> 查看状态\n"
        f"\n可用模式: {', '.join(sorted(REGISTRY))}"
    )


def _persist(state, **changes):
    """Apply changes to live cfg + write only those top-level keys to disk.

    Reads the file fresh so api_id/api_hash (which may come from env vars and
    not live in the file) are never written or overwritten here.
    """
    state.cfg.update(changes)
    try:
        with open(state.config_path, encoding="utf-8") as f:
            raw = json.load(f)
        raw.update(changes)
        with open(state.config_path, "w", encoding="utf-8") as f:
            json.dump(raw, f, ensure_ascii=False, indent=2)
    except Exception as e:
        log.warning("persist failed: %s", e)


def register_control(client, state):
    ctrl = state.cfg.get("control") or {}
    if not ctrl.get("enabled", True):
        log.info("control panel disabled")
        return
    trigger = ctrl.get("trigger", "⚙️")
    cprefix = ctrl.get("prefix", ".")
    chat = ctrl.get("chat", "me")

    @client.on(events.NewMessage(outgoing=True, chats=chat))
    async def _handler(event):
        text = (event.raw_text or "").strip()

        # bare emoji -> open the panel
        if text == trigger:
            await event.edit(_panel(state, cprefix), parse_mode="html")
            return

        if not text.startswith(cprefix):
            return  # an ordinary saved message, leave it alone

        body = text[len(cprefix):]
        cmd, _, rest = body.partition(" ")
        cmd = cmd.lower()
        arg = rest if cmd == "sep" else rest.strip()  # sep keeps spaces

        async def reply(msg):
            await event.edit(msg, parse_mode="html")

        if cmd == "mode":
            if arg in REGISTRY:
                _persist(state, mode=arg)
                state.wake()
                await reply(f"✅ 模式 → <b>{arg}</b>")
            else:
                await reply(f"❌ 未知模式: {arg}\n可用: {', '.join(sorted(REGISTRY))}")
        elif cmd == "prefix":
            _persist(state, prefix=arg)
            state.wake()
            await reply(f"✅ 前缀 → <b>{arg}</b>")
        elif cmd == "sep":
            _persist(state, separator=arg or " ")
            state.wake()
            await reply(f"✅ 分隔符 → '<b>{arg or ' '}</b>'")
        elif cmd == "interval":
            if arg.isdigit():
                _persist(state, update_interval=max(10, int(arg)))
                state.wake()
                await reply(f"✅ 间隔 → {state.cfg['update_interval']}s")
            else:
                await reply("❌ 用法: 间隔为整数秒，例如 <code>120</code>")
        elif cmd == "tz":
            try:
                from zoneinfo import ZoneInfo
                ZoneInfo(arg)
                _persist(state, timezone=arg)
                state.wake()
                await reply(f"✅ 时区 → <b>{arg}</b>")
            except Exception:
                await reply(f"❌ 无效时区: {arg}（例如 Asia/Shanghai）")
        elif cmd == "off":
            state.paused = True
            await reply("⏸ 已暂停更新")
        elif cmd == "on":
            state.paused = False
            state.wake()
            await reply("▶ 已恢复更新")
        elif cmd == "status":
            await reply(_status(state))
        # unknown dot-command: ignore silently
