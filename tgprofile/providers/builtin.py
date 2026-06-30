"""Built-in profile providers. Add your own with @provider("name")."""

import asyncio
import re
import time as _time
from datetime import datetime

import httpx

from . import provider

# --------------------------------------------------------------------------
# tiny async TTL cache (so weather/crypto aren't hammered every loop)
# --------------------------------------------------------------------------
_CACHE = {}


async def cached(key, ttl, coro_fn):
    now = _time.time()
    hit = _CACHE.get(key)
    if hit and now - hit[0] < ttl:
        return hit[1]
    val = await coro_fn()
    _CACHE[key] = (now, val)
    return val


# --------------------------------------------------------------------------
# time / date / weekday
# --------------------------------------------------------------------------
@provider("time")
async def mode_time(ctx):
    return ctx.compose(ctx.now.strftime(ctx.opts.get("format", "%H:%M")))


@provider("datetime")
async def mode_datetime(ctx):
    return ctx.compose(ctx.now.strftime(ctx.opts.get("format", "%m/%d %H:%M")))


_WEEKDAY = {
    "zh": ["周一", "周二", "周三", "周四", "周五", "周六", "周日"],
    "en": ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"],
}


@provider("weekday")
async def mode_weekday(ctx):
    names = _WEEKDAY.get(ctx.opts.get("lang", "zh"), _WEEKDAY["zh"])
    return ctx.compose(names[ctx.now.weekday()])


@provider("daynight")
async def mode_daynight(ctx):
    o = ctx.opts
    h = ctx.now.hour
    is_day = o.get("day_start", 6) <= h < o.get("night_start", 18)
    emoji = o.get("day_emoji", "☀️") if is_day else o.get("night_emoji", "🌙")
    t = ctx.now.strftime(o.get("format", "%H:%M"))
    return f"{emoji} {ctx.prefix}{ctx.separator}{t}"


# --------------------------------------------------------------------------
# weather (Open-Meteo, no API key)
# --------------------------------------------------------------------------
_WMO = {
    0: "☀️", 1: "🌤️", 2: "⛅", 3: "☁️",
    45: "🌫️", 48: "🌫️",
    51: "🌦️", 53: "🌦️", 55: "🌦️",
    61: "🌧️", 63: "🌧️", 65: "🌧️",
    71: "🌨️", 73: "🌨️", 75: "❄️",
    80: "🌦️", 81: "🌧️", 82: "⛈️",
    95: "⛈️", 96: "⛈️", 99: "⛈️",
}


@provider("weather")
async def mode_weather(ctx):
    o = ctx.opts
    lat, lon = o.get("lat"), o.get("lon")
    if lat is None or lon is None:
        return ctx.compose("📍set lat/lon")

    async def fetch():
        url = "https://api.open-meteo.com/v1/forecast"
        params = {"latitude": lat, "longitude": lon,
                  "current": "temperature_2m,weather_code"}
        async with httpx.AsyncClient(timeout=10) as c:
            r = await c.get(url, params=params)
            cur = r.json()["current"]
            return cur["temperature_2m"], cur["weather_code"]

    temp, code = await cached(f"weather:{lat},{lon}", o.get("cache_ttl", 1800), fetch)
    return ctx.compose(f"{_WMO.get(code, '🌡️')}{round(temp)}°C")


# --------------------------------------------------------------------------
# system (CPU / RAM)  — needs psutil
# --------------------------------------------------------------------------
@provider("system")
async def mode_system(ctx):
    import psutil
    cpu = psutil.cpu_percent(interval=None)
    ram = psutil.virtual_memory().percent
    fmt = ctx.opts.get("format", "CPU {cpu:.0f}% RAM {ram:.0f}%")
    return ctx.compose(fmt.format(cpu=cpu, ram=ram))


# --------------------------------------------------------------------------
# ping
# --------------------------------------------------------------------------
async def _ping(host, timeout=2):
    try:
        proc = await asyncio.create_subprocess_exec(
            "ping", "-c", "1", "-W", str(timeout), host,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.DEVNULL,
        )
        out, _ = await proc.communicate()
        if proc.returncode != 0:
            return None
        m = re.search(r"time=([\d.]+)", out.decode())
        return round(float(m.group(1))) if m else None
    except Exception:
        return None


@provider("ping")
async def mode_ping(ctx):
    o = ctx.opts
    label = o.get("label", "")
    ms = await _ping(o.get("host", "1.1.1.1"))
    body = f"{label} {ms}ms" if ms is not None else f"{label} timeout"
    return ctx.compose(body.strip())


# --------------------------------------------------------------------------
# crypto (CoinGecko)
# --------------------------------------------------------------------------
_COINGECKO = {
    "BTC": "bitcoin", "ETH": "ethereum", "BNB": "binancecoin",
    "SOL": "solana", "XRP": "ripple", "DOGE": "dogecoin",
    "TON": "the-open-network", "USDT": "tether",
}


def _human_price(v):
    v = float(v)
    if v >= 1000:
        return f"{v / 1000:.1f}k".replace(".0k", "k")
    if v >= 1:
        return f"{v:.0f}"
    return f"{v:.4f}".rstrip("0").rstrip(".")


@provider("crypto")
async def mode_crypto(ctx):
    o = ctx.opts
    sym = o.get("symbol", "BTC").upper()
    vs = o.get("vs", "usd")
    cid = _COINGECKO.get(sym, sym.lower())

    async def fetch():
        url = "https://api.coingecko.com/api/v3/simple/price"
        async with httpx.AsyncClient(timeout=10) as c:
            r = await c.get(url, params={"ids": cid, "vs_currencies": vs})
            return r.json()[cid][vs]

    price = await cached(f"crypto:{cid}:{vs}", o.get("cache_ttl", 120), fetch)
    return ctx.compose(f"{sym} {_human_price(price)}")


# --------------------------------------------------------------------------
# countdown
# --------------------------------------------------------------------------
@provider("countdown")
async def mode_countdown(ctx):
    o = ctx.opts
    target = datetime.strptime(o["target"], "%Y-%m-%d").date()
    days = (target - ctx.now.date()).days
    label = o.get("label", "")
    return ctx.compose(f"{label} {days}D".strip())


# --------------------------------------------------------------------------
# holiday
# --------------------------------------------------------------------------
@provider("holiday")
async def mode_holiday(ctx):
    dates = ctx.opts.get("dates", {"01-01": "🎆", "12-25": "🎄", "10-31": "🎃"})
    emoji = dates.get(ctx.now.strftime("%m-%d"))
    return f"{emoji} {ctx.prefix}" if emoji else ctx.prefix


# --------------------------------------------------------------------------
# custom template
# --------------------------------------------------------------------------
@provider("custom")
async def mode_custom(ctx):
    o = ctx.opts
    return o.get("template", "{prefix} {time}").format(
        prefix=ctx.prefix,
        sep=ctx.separator,
        time=ctx.now.strftime(o.get("time_format", "%H:%M")),
        date=ctx.now.strftime(o.get("date_format", "%m/%d")),
    )
