from telethon import TelegramClient


def build_client(cfg):
    return TelegramClient(cfg["session"], cfg["api_id"], cfg["api_hash"])
