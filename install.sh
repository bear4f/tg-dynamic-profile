#!/usr/bin/env bash
# VPS（Debian/Ubuntu）一键安装脚本，需以 root 运行。
set -euo pipefail

APP_DIR=/opt/tg-dynamic-profile
SRC_DIR="$(cd "$(dirname "$0")" && pwd)"

echo ">>> 安装到 $APP_DIR"
mkdir -p "$APP_DIR"
cp -r "$SRC_DIR"/. "$APP_DIR"/
cd "$APP_DIR"

echo ">>> 创建 venv + 安装依赖"
python3 -m venv .venv
.venv/bin/pip install --upgrade pip
.venv/bin/pip install -r requirements.txt

if [ ! -f config.json ]; then
  cp config.example.json config.json
  echo ">>> 已生成 config.json，请先填写 api_id / api_hash（或直接运行下面的向导）。"
fi

# 注册 `emoji` 命令：以后在终端敲 emoji 就能快速打开交互菜单（改模式/前缀/参数）
RC_FILE="$HOME/.bashrc"
if ! grep -qF "alias emoji=" "$RC_FILE" 2>/dev/null; then
  {
    echo ""
    echo "# tg-dynamic-profile: 输入 emoji 快速打开交互菜单"
    echo "alias emoji='cd \"$APP_DIR\" && .venv/bin/python app.py menu'"
  } >> "$RC_FILE"
  echo ">>> 已在 $RC_FILE 里添加 'emoji' 命令，执行 'source $RC_FILE'（或重新登录终端）后即可使用"
fi

echo ""
echo ">>> 后续步骤（推荐用向导，全程中文引导，自动完成填凭证+登录）："
echo "    $APP_DIR/.venv/bin/python app.py setup"
echo ""
echo ">>> 或手动操作："
echo "    1) nano $APP_DIR/config.json          # 填写 api_id / api_hash"
echo "    2) cd $APP_DIR && .venv/bin/python app.py login   # 首次登录"
echo "    3) cp systemd/tg-profile.service /etc/systemd/system/"
echo "       systemctl daemon-reload && systemctl enable --now tg-profile"
echo "       journalctl -u tg-profile -f"
echo ""
echo ">>> 改配置(新终端): 敲 emoji  （或 cd $APP_DIR && .venv/bin/python app.py menu），保存后几秒内自动生效"
