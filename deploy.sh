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
.venv/bin/python app.py setup

# 注册 `emoji` 命令：以后在终端敲 emoji 就能快速打开交互菜单（改模式/前缀/参数）。
# 用函数而不是写死路径的 alias，优先找 systemd 里 tg-profile.service 真正在用的
# 目录——如果之前用 deploy.sh 装过一次、又用 install.sh 装了 systemd 服务，两边
# 目录不一致的话，写死路径的 alias 会一直指向第一次装的那份，改配置就不会生效。
RC_FILE="$HOME/.bashrc"
BEGIN_MARK="# >>> tg-dynamic-profile emoji shortcut >>>"
END_MARK="# <<< tg-dynamic-profile emoji shortcut <<<"
touch "$RC_FILE"
sed -i "/$BEGIN_MARK/,/$END_MARK/d" "$RC_FILE"
sed -i "/tg-dynamic-profile: 输入 emoji 快速打开交互菜单/d; /^alias emoji=/d" "$RC_FILE"
{
  echo ""
  echo "$BEGIN_MARK"
  echo "# 由 deploy.sh/install.sh 自动生成，不要手动改；重新运行装脚本会自动更新"
  echo "emoji() {"
  echo "  local dir"
  echo "  dir=\$(systemctl show tg-profile.service -p WorkingDirectory --value 2>/dev/null)"
  echo "  if [ -z \"\$dir\" ] || [ ! -d \"\$dir\" ]; then"
  echo "    dir=\"$DIR\""
  echo "  fi"
  echo "  ( cd \"\$dir\" && .venv/bin/python app.py menu )"
  echo "}"
  echo "$END_MARK"
} >> "$RC_FILE"
echo ">>> 已在 $RC_FILE 里注册 'emoji' 命令，执行 'source $RC_FILE'（或重新登录终端）后即可使用"

echo ""
echo ">>> 前台运行:      cd $DIR && .venv/bin/python app.py run"
echo ">>> 改配置(新终端): 敲 emoji  （或 cd $DIR && .venv/bin/python app.py menu）"
