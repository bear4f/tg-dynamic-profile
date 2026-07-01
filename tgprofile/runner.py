import asyncio
import logging
import os
import time as time_module
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional
from zoneinfo import ZoneInfo

from telethon.errors import FloodWaitError
from telethon.tl.functions.account import UpdateProfileRequest

from .client import build_client
from .config import load_config
from .control import DEFAULT_TRIGGERS, _normalize_triggers, register_control
from .fonts import apply_style, normalize_style
from .providers import REGISTRY

log = logging.getLogger("tgprofile")
NAME_MAX = 64  # Telegram first_name hard limit


@dataclass
class Ctx:
    now: datetime
    prefix: str
    separator: str
    opts: dict
    font_style: str = "plain"

    def compose(self, body):
        return f"{self.prefix}{self.separator}{body}"

    def stylize(self, text):
        return apply_style(text, self.font_style)


@dataclass
class State:
    """Shared, mutable runtime state. The control panel edits cfg live."""
    cfg: dict
    config_path: str
    paused: bool = False
    last_name: Optional[str] = None
    last_set_at: Optional[float] = None
    poke: Optional[asyncio.Event] = field(default=None)

    def wake(self):
        """Ask the updater to re-render immediately (after a live change)."""
        if self.poke:
            self.poke.set()


async def render_profile_name(cfg):
    mode = cfg["mode"]
    fn = REGISTRY.get(mode)
    if fn is None:
        raise ValueError(f"unknown mode '{mode}'")

    font_style = normalize_style(cfg.get("font_style", "plain"))
    now = datetime.now(ZoneInfo(cfg.get("timezone", "UTC")))
    opts = cfg.get("modes", {}).get(mode, {})
    ctx = Ctx(
        now,
        cfg.get("prefix", ""),
        cfg.get("separator", " "),
        opts,
        font_style,
    )
    return apply_style(await fn(ctx), font_style)[:NAME_MAX]


async def _updater(client, state):
    last = None
    while True:
        delay = max(int(state.cfg.get("update_interval", 60)), 10)
        try:
            if not state.paused:
                cfg = state.cfg
                mode = cfg["mode"]
                fn = REGISTRY.get(mode)
                if fn is None:
                    log.error("unknown mode '%s'", mode)
                else:
                    name = await render_profile_name(cfg)
                    if name != last:
                        result = await client(UpdateProfileRequest(first_name=name))
                        last = name
                        # account.updateProfile 返回的 User 才是服务器真正存下的名字：
                        # 它可能会把花体字过滤/还原成普通字母，这里直接用服务器的回包
                        # 判断，而不是假设发出去的就是最终显示的——这才是"有时候花体、
                        # 有时候变回默认"的真实原因：服务器过滤不是每次都触发，不是本
                        # 程序的 bug，只是之前没把这个差异打到日志里，看起来就很随机。
                        confirmed = getattr(result, "first_name", None) or name
                        state.last_name = confirmed
                        state.last_set_at = time_module.time()
                        if confirmed != name:
                            log.warning(
                                "name -> %s（⚠️ Telegram 服务器把它还原成了 %s，"
                                "花体字被过滤，非本程序问题）", name, confirmed)
                        else:
                            log.info("name -> %s", name)
        except FloodWaitError as e:
            log.warning("FloodWait: sleeping %ss", e.seconds)
            await asyncio.sleep(e.seconds + 5)
            continue
        except Exception as e:
            log.error("update failed: %s", e)

        # 睡到下一个整点对齐的检查点，而不是"从现在起等 delay 秒"——
        # 否则每次检查的相位取决于进程启动时刻，time/datetime 等按分钟显示的
        # 模式最多会滞后接近一个 delay（比如 interval=60 时最多滞后 59 秒）。
        # 对齐后，interval=60 时检查点固定在每分钟的 :00 秒，基本无延迟。
        aligned_wait = max(delay - (time_module.time() % delay), 1)
        try:
            await asyncio.wait_for(state.poke.wait(), timeout=aligned_wait)
            state.poke.clear()
            last = None
        except asyncio.TimeoutError:
            pass


async def _self_check(client, state, interval=15):
    """定期主动重新查询 Telegram 上现在真正存的名字。

    实测发现：调用 account.updateProfile 那一刻的回包会确认花体字符已经被接受，
    但过一段时间后 Telegram 会在后台悄悄把它异步还原成普通字母——只看更新那一刻
    的回包完全发现不了这种"延迟生效"的还原。这里独立于更新循环，定期主动问一次
    服务器现在到底是什么，才能抓到这种事后被改的情况，并记录大概过了多久发生。
    """
    while True:
        await asyncio.sleep(interval)
        if not state.last_name:
            continue
        try:
            me = await client.get_me()
        except Exception as e:
            log.debug("self-check get_me failed: %s", e)
            continue
        if me.first_name != state.last_name:
            elapsed = time_module.time() - (state.last_set_at or time_module.time())
            log.warning(
                "自检发现昵称被后台改成了 %s（原来是 %s，设置后约 %.0f 秒发生，"
                "推测是 Telegram 异步还原花体字符，不是本程序改的）",
                me.first_name, state.last_name, elapsed)
            state.last_name = me.first_name
            state.last_set_at = time_module.time()


async def _config_watcher(state, interval=3):
    """轮询 config.json 的修改时间，检测到变化就重新加载。

    这样 `python app.py menu` 在终端里改完配置，正在运行的 `app.py run`
    几秒内就能自动生效，不需要重启进程，也不需要走 Telegram 收藏夹。
    """
    path = state.config_path
    try:
        last_mtime = os.path.getmtime(path)
    except OSError:
        last_mtime = None

    while True:
        await asyncio.sleep(interval)
        try:
            mtime = os.path.getmtime(path)
        except OSError:
            continue
        if mtime == last_mtime:
            continue
        last_mtime = mtime
        try:
            new_cfg = load_config(path)
        except SystemExit as e:
            log.warning("config.json 已更新但加载失败，忽略本次变更: %s", e)
            continue
        state.cfg.update(new_cfg)
        state.wake()
        log.info("检测到 config.json 变更，已重新加载 | mode=%s prefix=%s",
                  state.cfg.get("mode"), state.cfg.get("prefix"))


async def run_loop(config_path):
    logging.basicConfig(level=logging.INFO,
                        format="%(asctime)s %(levelname)s %(message)s")
    cfg = load_config(config_path)
    if cfg["mode"] not in REGISTRY:
        raise SystemExit(
            f"未知模式 '{cfg['mode']}'。可用模式: {', '.join(sorted(REGISTRY))}")

    client = build_client(cfg)
    await client.connect()
    if not await client.is_user_authorized():
        raise SystemExit("尚未登录，请先运行 `python app.py login`。")

    me = await client.get_me()
    state = State(cfg=cfg, config_path=config_path, poke=asyncio.Event())
    register_control(client, state)

    ctrl_enabled = (cfg.get("control") or {}).get("enabled", True)
    extra = ""
    if ctrl_enabled:
        triggers = _normalize_triggers((cfg.get("control") or {}).get("trigger", DEFAULT_TRIGGERS))
        extra = f" | Telegram 面板(可选): 在收藏夹发送 '{' / '.join(triggers)}'"
    log.info("Logged in as @%s | mode=%s | app=%s | config=%s | 改配置用 `python app.py menu`（几秒内自动生效，不用重启）%s",
             me.username or me.first_name, cfg["mode"], os.path.dirname(os.path.dirname(__file__)),
             os.path.abspath(config_path), extra)

    client.loop.create_task(_updater(client, state))
    client.loop.create_task(_config_watcher(state))
    client.loop.create_task(_self_check(client, state))
    await client.run_until_disconnected()
