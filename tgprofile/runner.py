import asyncio
import logging
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional
from zoneinfo import ZoneInfo

from telethon.errors import FloodWaitError
from telethon.tl.functions.account import UpdateProfileRequest

from .client import build_client
from .config import load_config
from .control import DEFAULT_TRIGGERS, _normalize_triggers, register_control
from .providers import REGISTRY

log = logging.getLogger("tgprofile")
NAME_MAX = 64  # Telegram first_name hard limit


@dataclass
class Ctx:
    now: datetime
    prefix: str
    separator: str
    opts: dict

    def compose(self, body):
        return f"{self.prefix}{self.separator}{body}"


@dataclass
class State:
    """Shared, mutable runtime state. The control panel edits cfg live."""
    cfg: dict
    config_path: str
    paused: bool = False
    poke: Optional[asyncio.Event] = field(default=None)

    def wake(self):
        """Ask the updater to re-render immediately (after a live change)."""
        if self.poke:
            self.poke.set()


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
                    now = datetime.now(ZoneInfo(cfg.get("timezone", "UTC")))
                    opts = cfg.get("modes", {}).get(mode, {})
                    ctx = Ctx(now, cfg.get("prefix", ""), cfg.get("separator", " "), opts)
                    name = (await fn(ctx))[:NAME_MAX]
                    if name != last:
                        await client(UpdateProfileRequest(first_name=name))
                        last = name
                        log.info("name -> %s", name)
        except FloodWaitError as e:
            log.warning("FloodWait: sleeping %ss", e.seconds)
            await asyncio.sleep(e.seconds + 5)
            continue
        except Exception as e:
            log.error("update failed: %s", e)

        # sleep until next tick, but wake early (and force re-render) on a live change
        try:
            await asyncio.wait_for(state.poke.wait(), timeout=delay)
            state.poke.clear()
            last = None
        except asyncio.TimeoutError:
            pass


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

    triggers = _normalize_triggers((cfg.get("control") or {}).get("trigger", DEFAULT_TRIGGERS))
    log.info("Logged in as @%s | mode=%s | 控制面板: 在收藏夹发送 '%s'",
             me.username or me.first_name, cfg["mode"], " / ".join(triggers))

    client.loop.create_task(_updater(client, state))
    await client.run_until_disconnected()
