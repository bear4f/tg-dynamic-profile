import json
import os

DEFAULTS = {
    "api_id": 0,
    "api_hash": "",
    "session": "tg_profile",
    "mode": "time",
    "prefix": "",
    "separator": " ",
    "timezone": "UTC",
    "update_interval": 60,
    "modes": {},
}


def load_config(path):
    """Load config.json, merge with defaults, allow env overrides for secrets."""
    with open(path, encoding="utf-8") as f:
        cfg = json.load(f)
    merged = {**DEFAULTS, **cfg}
    merged["api_id"] = int(os.environ.get("TG_API_ID", merged.get("api_id") or 0))
    merged["api_hash"] = os.environ.get("TG_API_HASH", merged.get("api_hash") or "")
    if not merged["api_id"] or not merged["api_hash"]:
        raise SystemExit(
            "Missing api_id/api_hash. Set them in config.json or via "
            "TG_API_ID / TG_API_HASH env vars (get them at https://my.telegram.org)."
        )
    return merged


def save_config(path, cfg):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(cfg, f, ensure_ascii=False, indent=2)
