#!/usr/bin/env bash
# One-line deploy:
#   bash <(curl -fsSL https://raw.githubusercontent.com/bear4f/tg-dynamic-profile/main/deploy.sh)
#
# Clones the repo, builds a venv, installs deps, then launches the guided
# setup wizard (API creds -> login -> mode). Re-runnable / idempotent.
set -euo pipefail

REPO="${TGP_REPO:-https://github.com/bear4f/tg-dynamic-profile.git}"
DIR="${TGP_DIR:-$HOME/tg-dynamic-profile}"

need() { command -v "$1" >/dev/null 2>&1 || { echo "❌ 需要先安装: $1"; exit 1; }; }
need git
need python3

echo ">>> 目标目录: $DIR"
if [ -d "$DIR/.git" ]; then
  echo ">>> 已存在，拉取更新"
  git -C "$DIR" pull --ff-only || true
else
  git clone --depth 1 "$REPO" "$DIR"
fi

cd "$DIR"
echo ">>> 创建 venv + 安装依赖"
python3 -m venv .venv
.venv/bin/pip install --upgrade pip -q
.venv/bin/pip install -r requirements.txt -q

echo ">>> 启动交互式安装向导"
exec .venv/bin/python app.py setup
