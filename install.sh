#!/usr/bin/env bash
# VPS（Debian/Ubuntu）一键安装脚本，需以 root 运行。
set -euo pipefail

APP_DIR=/opt/tg-dynamic-profile
SRC_DIR="$(cd "$(dirname "$0")" && pwd)"

echo ">>> 安装到 $APP_DIR"
mkdir -p "$APP_DIR"
if [ "$SRC_DIR" != "$APP_DIR" ]; then
  cp -r "$SRC_DIR"/. "$APP_DIR"/
else
  echo ">>> 已经在 $APP_DIR 里面运行（比如 git pull 之后重新装），跳过复制"
fi
cd "$APP_DIR"

echo ">>> 创建 venv + 安装依赖"
python3 -m venv .venv
.venv/bin/pip install --upgrade pip
.venv/bin/pip install -r requirements.txt

if [ ! -f config.json ]; then
  cp config.example.json config.json
  echo ">>> 已生成 config.json，请先填写 api_id / api_hash（或直接运行下面的向导）。"
fi

# 注册 `emoji` 命令：以后在终端敲 emoji 就能快速打开交互菜单（改模式/前缀/参数）。
# 用函数而不是写死路径的 alias，优先找 systemd 里 tg-profile.service 真正在用的
# 目录——如果之前用 deploy.sh 装过一次、又用这个脚本装了 systemd 服务，两边目录
# 不一致的话，写死路径的 alias 会一直指向第一次装的那份，改配置就不会生效。
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
  echo "    dir=\"$APP_DIR\""
  echo "  fi"
  echo "  ( cd \"\$dir\" && .venv/bin/python app.py menu )"
  echo "}"
  echo "$END_MARK"
} >> "$RC_FILE"
echo ">>> 已在 $RC_FILE 里注册 'emoji' 命令，执行 'source $RC_FILE'（或重新登录终端）后即可使用"

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
