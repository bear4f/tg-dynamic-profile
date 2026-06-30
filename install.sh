#!/usr/bin/env bash
# One-shot installer for VPS (Debian/Ubuntu). Run as root.
set -euo pipefail

APP_DIR=/opt/tg-dynamic-profile
SRC_DIR="$(cd "$(dirname "$0")" && pwd)"

echo ">>> Installing to $APP_DIR"
mkdir -p "$APP_DIR"
cp -r "$SRC_DIR"/. "$APP_DIR"/
cd "$APP_DIR"

echo ">>> Creating venv + installing deps"
python3 -m venv .venv
.venv/bin/pip install --upgrade pip
.venv/bin/pip install -r requirements.txt

if [ ! -f config.json ]; then
  cp config.example.json config.json
  echo ">>> Created config.json — edit it now (api_id / api_hash / prefix / mode)."
fi

echo ""
echo ">>> Next steps:"
echo "    1) nano $APP_DIR/config.json          # fill api_id / api_hash"
echo "    2) cd $APP_DIR && .venv/bin/python app.py login   # one-time login"
echo "    3) cp systemd/tg-profile.service /etc/systemd/system/"
echo "       systemctl daemon-reload && systemctl enable --now tg-profile"
echo "       journalctl -u tg-profile -f"
