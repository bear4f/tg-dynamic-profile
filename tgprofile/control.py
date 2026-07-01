"""文字触发的实时控制面板。

在 Telegram 收藏夹发送触发词（默认中/英文 `面板` / `panel`，不依赖表情符号，
因为不同手机/输入法发出的 emoji 编码不一致，可能导致精确匹配失败），运行中的
userbot 会把消息就地编辑成控制面板。之后在同一对话发送点命令即可实时修改设置，
例如 `.mode weather`、`.prefix Bob`、`.interval 120`、`.off`。

触发词也可以自己改成表情或其它文字（见 config.json 的 control.trigger，支持
单个字符串或字符串列表），文字匹配不区分大小写。
"""
import asyncio
import html
import json
import logging
import shutil
from pathlib import Path

from telethon import events

from .fonts import STYLE_ORDER, is_known_style, normalize_style, style_example
from .providers import REGISTRY

log = logging.getLogger("tgprofile")

DEFAULT_TRIGGERS = ["面板", "panel"]
APP_DIR = Path(__file__).resolve().parents[1]


def _normalize_triggers(raw):
    """control.trigger 支持单个字符串或字符串列表，统一成去空白的列表。"""
    if not raw:
        return DEFAULT_TRIGGERS
    values = raw if isinstance(raw, (list, tuple)) else [raw]
    return [str(v).strip() for v in values if str(v).strip()] or DEFAULT_TRIGGERS


def _status(state):
    c = state.cfg
    flag = "⏸ 已暂停" if state.paused else "▶ 运行中"
    last_name = state.last_name or "等待首次更新"
    return (
        f"{flag}\n"
        f"mode=<b>{html.escape(str(c['mode']))}</b> "
        f"font=<b>{html.escape(normalize_style(c.get('font_style', 'plain')))}</b> "
        f"interval={c.get('update_interval', 60)}s "
        f"tz={html.escape(str(c.get('timezone', 'UTC')))}\n"
        f"prefix=<b>{html.escape(str(c.get('prefix', '')))}</b> "
        f"sep='<b>{html.escape(str(c.get('separator', ' ')))}</b>'\n"
        f"当前昵称: <code>{html.escape(last_name)}</code>\n"
        f"运行目录: <code>{html.escape(str(APP_DIR))}</code>\n"
        f"配置文件: <code>{html.escape(str(Path(state.config_path).resolve()))}</code>"
    )


def _panel(state, cprefix, triggers):
    return (
        "⚙️ <b>Dynamic Profile 控制面板</b>\n"
        f"{_status(state)}\n"
        "──────────────\n"
        "在本对话直接发送命令修改：\n"
        f"• <code>{cprefix}mode &lt;名称&gt;</code> 切换模式\n"
        f"• <code>{cprefix}prefix &lt;文本&gt;</code> 改前缀\n"
        f"• <code>{cprefix}font &lt;样式&gt;</code> 改字体（plain/script/bold/monospace...）\n"
        f"• <code>{cprefix}interval &lt;秒&gt;</code> 改刷新间隔\n"
        f"• <code>{cprefix}sep &lt;字符&gt;</code> 改分隔符\n"
        f"• <code>{cprefix}tz &lt;时区&gt;</code> 改时区\n"
        f"• <code>{cprefix}update</code> 拉取最新脚本\n"
        f"• <code>{cprefix}off</code> / <code>{cprefix}on</code> 暂停/恢复\n"
        f"• <code>{cprefix}status</code> 查看状态\n"
        f"\n可用模式: {', '.join(sorted(REGISTRY))}"
        f"\n触发词: {' / '.join(triggers)}"
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


def _trim_output(text, limit=2400):
    text = (text or "").strip()
    if len(text) <= limit:
        return text
    return "...\n" + text[-limit:]


async def _pull_latest():
    git = shutil.which("git")
    if not git:
        return "❌ 服务器未找到 git，无法自动拉取。请先在 VPS 安装 git。"
    if not (APP_DIR / ".git").exists():
        return (
            "❌ 当前目录不是 git 仓库，无法自动拉取。\n"
            f"目录: <code>{html.escape(str(APP_DIR))}</code>"
        )

    try:
        proc = await asyncio.create_subprocess_exec(
            git, "-C", str(APP_DIR), "pull", "--ff-only",
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        out, err = await asyncio.wait_for(proc.communicate(), timeout=120)
    except asyncio.TimeoutError:
        proc.kill()
        await proc.wait()
        return "❌ 更新超时，请稍后重试或 SSH 到服务器手动检查。"
    except Exception as e:
        return f"❌ 更新失败: <code>{html.escape(str(e))}</code>"

    output = (out + err).decode(errors="replace").strip() or "(无输出)"
    output = html.escape(_trim_output(output))
    if proc.returncode == 0:
        return (
            "✅ 已拉取最新脚本\n"
            f"<code>{output}</code>\n\n"
            "如果更新了 Python 代码，未安装 systemd 服务时请重启当前进程；"
            "已安装服务时运行 <code>systemctl restart tg-profile</code> 后生效。"
        )
    return (
        "❌ 更新失败\n"
        f"<code>{output}</code>\n\n"
        "提示：自动更新只支持 fast-forward；如果服务器上有本地改动，"
        "需要 SSH 登录后手动处理。"
    )


def register_control(client, state):
    ctrl = state.cfg.get("control") or {}
    if not ctrl.get("enabled", True):
        log.info("control panel disabled")
        return
    triggers = _normalize_triggers(ctrl.get("trigger", DEFAULT_TRIGGERS))
    triggers_lower = [t.lower() for t in triggers]
    cprefix = ctrl.get("prefix", ".")
    chat = ctrl.get("chat", "me")

    @client.on(events.NewMessage(outgoing=True, chats=chat))
    async def _handler(event):
        text = (event.raw_text or "").strip()

        # 发送触发词（不区分大小写）-> 打开面板
        if text.lower() in triggers_lower:
            await event.edit(_panel(state, cprefix, triggers), parse_mode="html")
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
        elif cmd == "font":
            if not is_known_style(arg):
                await reply(
                    "❌ 未知字体样式: "
                    f"{arg}\n可用: {', '.join(STYLE_ORDER)}"
                )
                return
            style = normalize_style(arg)
            _persist(state, font_style=style)
            state.wake()
            await reply(
                f"✅ 字体 → <b>{style}</b>\n"
                f"示例: <code>{style_example(style)}</code>\n"
                "几秒内会整体应用到前缀和动态内容；发送 "
                f"<code>{cprefix}status</code> 可查看实际昵称。"
            )
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
        elif cmd in {"update", "pull"}:
            await reply("⏳ 正在拉取最新脚本，请稍等...")
            await reply(await _pull_latest())
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
