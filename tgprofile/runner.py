import asyncio
import logging
from dataclasses import dataclass
from datetime import datetime
from zoneinfo import ZoneInfo

from telethon.errors import FloodWaitError
from telethon.tl.functions.account import UpdateProfileRequest

from .client import build_client
from .config import load_config
from .providers import REGISTRY

log = logging.getLogger("tgprofile")

# Telegram first_name hard limit
NAME_MAX = 64


@dataclass
class Ctx:
    now: datetime
    prefix: str
    separator: str
    opts: dict

    def compose(self, body):
        return f"{self.prefix}{self.separator}{body}"


async def run_loop(config_path):
    logging.basicConfig(level=logging.INFO,
                        format="%(asctime)s %(levelname)s %(message)s")
    cfg = load_config(config_path)
    mode = cfg["mode"]
    if mode not in REGISTRY:
        raise SystemExit(
            f"Unknown mode '{mode}'. Available: {', '.join(sorted(REGISTRY))}")

    fn = REGISTRY[mode]
    tz = ZoneInfo(cfg["timezone"])
    interval = max(int(cfg["update_interval"]), 10)

    client = build_client(cfg)
    await client.connect()
    if not await client.is_user_authorized():
        raise SystemExit("Not authorized. Run `python app.py login` first.")

    me = await client.get_me()
    log.info("Logged in as @%s | mode=%s | interval=%ss",
             me.username or me.first_name, mode, interval)

    last = None
    while True:
        try:
            now = datetime.now(tz)
            opts = cfg.get("modes", {}).get(mode, {})
            ctx = Ctx(now, cfg["prefix"], cfg["separator"], opts)
            name = (await fn(ctx))[:NAME_MAX]
            if name != last:
                await client(UpdateProfileRequest(first_name=name))
                last = name
                log.info("name -> %s", name)
        except FloodWaitError as e:
            log.warning("FloodWait: sleeping %ss", e.seconds)
            await asyncio.sleep(e.seconds + 5)
            continue
        except Exception as e:  # keep the loop alive on transient errors
            log.error("update failed: %s", e)
        await asyncio.sleep(interval)
