# TG Dynamic Profile · Telegram 动态昵称系统

用你自己的 Telegram 账号（userbot），让昵称（First Name）**自动变化**：实时时间、日期星期、天气、CPU/RAM、延迟、币价、倒计时、节日……全部由一个 **配置文件 + 菜单** 驱动，无需改 Python 代码。

```
YourName 09:15        # 时间
☀️ YourName 09:15      # 白天/夜晚
YourName ☀️28°C        # 天气
YourName BTC 108k      # 币价
YourName NewYear 156D  # 倒计时
🎄 YourName            # 节日
```

> 别人看到的是你**真实的昵称**（不是第三方客户端本地渲染），所有人可见。

---

## ⚠️ 重要提醒（先读）

- 这是 **userbot**（用你的个人账号自动操作），请使用**小号 / 自己的账号**，风险自负。
- Telegram 对 `account.updateProfile` 有**限流**。本项目默认 `update_interval = 60s`，并自动捕获 `FloodWait` 退避。**不要把间隔设到 10 秒以内**，否则容易被限流甚至封号。
- 仅在昵称内容**真的变化**时才发请求（内置去重），最大程度减少调用。

---

## 🚀 一键部署

一条命令拉起交互式安装向导（克隆 → 建 venv → 装依赖 → 引导填凭证、登录、选模式）：

```bash
bash <(curl -fsSL https://raw.githubusercontent.com/bear4f/tg-dynamic-profile/main/deploy.sh)
```

向导跑完后：
```bash
cd ~/tg-dynamic-profile
.venv/bin/python app.py run        # 启动（改配置见下面『修改配置』，几秒内自动生效，不用重启）
```

> 想常驻后台，见下方『部署为 systemd 服务』。

---

## 🎛 修改配置（终端菜单，运行时自动生效）

`app.py run` 启动之后**不用退出、不用重启**，另开一个 SSH 窗口跑菜单直接改：

```bash
cd ~/tg-dynamic-profile
.venv/bin/python app.py menu
```

全是数字/字母选项，1、2、3 选就行：切模式、改前缀、改分隔符、改刷新间隔、改时区、改当前模式的参数（比如天气的经纬度）、实时预览效果，改完 `q` 保存。**保存后几秒内，正在运行的 `app.py run` 会自动检测到 `config.json` 变化并重新加载**，不需要手动重启进程、也不需要在 Telegram 里操作。

如果是用 systemd 常驻的，菜单改完不用 `systemctl restart`，等几秒生效即可；只有改 `api_id`/`api_hash`/`session` 这类需要重新登录的项才需要重启。

> **快捷方式**：`deploy.sh` / `install.sh` 装好后会自动往 `~/.bashrc` 加一条 `emoji` 命令别名。新开一个终端窗口，直接敲 `emoji`（`source ~/.bashrc` 或重新登录终端后生效）就能秒开这个交互菜单，不用记路径也不用敲完整命令。已经部署过的实例手动加一行也一样：
> ```bash
> echo "alias emoji='cd ~/tg-dynamic-profile && .venv/bin/python app.py menu'" >> ~/.bashrc && source ~/.bashrc
> ```

---

## 📱（可选）Telegram 收藏夹面板

不想开终端时，也可以在 Telegram 里改。这个功能**默认关闭**，需要先在 `config.json` 打开：

```jsonc
"control": { "enabled": true, "trigger": ["面板", "panel"], "prefix": ".", "chat": "me" }
```

（或用 `python app.py menu` -> `c` -> `1` 打开）打开后：

1. 打开 **Saved Messages（收藏夹）**
2. 发送 `面板` 或 `panel`（默认中英文触发词都可用，不区分大小写）—— userbot 会把它就地编辑成控制面板
3. 在同一对话发送点命令实时修改：

```
.mode weather      切换模式
.prefix Bob        改前缀
.interval 120      改刷新间隔(秒)
.sep  |            改分隔符
.tz Asia/Shanghai  改时区
.off  /  .on       暂停 / 恢复更新
.status            查看当前状态
```

`trigger` 可以是单个字符串，也可以是字符串数组（同时支持多个别名，如中文+英文，甚至换成表情）。

> 仅在 `chat`（默认你自己的收藏夹）里的**你本人发出**的消息才会被识别，不会影响普通聊天。

---

## 功能模式

| mode | 效果示例 | 说明 |
|------|----------|------|
| `time` | `YourName 09:15` | 实时时间，`format` 可自定义 |
| `datetime` | `YourName 06/30 09:15` | 日期 + 时间 |
| `weekday` | `YourName 周二` / `Tue` | 星期（zh/en） |
| `daynight` | `☀️ YourName 09:15` / `🌙 …` | 按小时切换昼夜表情 |
| `weather` | `YourName ☀️28°C` | Open-Meteo 免 key，自动缓存 |
| `system` | `YourName CPU 12% RAM 43%` | 本机 CPU/RAM（VPS 运维） |
| `ping` | `YourName HK 23ms` | ping 某主机延迟 |
| `crypto` | `YourName BTC 108k` | CoinGecko 币价 |
| `countdown` | `YourName Exam 8D` | 倒计时天数 |
| `holiday` | `🎄 YourName` | 节日自动加表情 |
| `custom` | 任意模板 | `{prefix}/{time}/{date}` 占位符 |

模式是**插件式注册**的，加新功能只要在 `tgprofile/providers/builtin.py` 写一个带 `@provider("name")` 的函数即可。

---

## 安装

### 1. 获取 API 凭证
访问 https://my.telegram.org → API development tools → 创建应用，拿到 **api_id** 和 **api_hash**。

### 2. 部署
```bash
git clone https://github.com/bear4f/tg-dynamic-profile.git
cd tg-dynamic-profile

python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

**最省事**：直接跑向导，一步到位（填凭证 → 登录 → 选模式）：
```bash
python app.py setup
```

或手动：
```bash
cp config.example.json config.json
# 编辑 config.json，填入 api_id / api_hash / prefix / mode
```

也可用环境变量代替（推荐，不把密钥写进文件）：
```bash
export TG_API_ID=123456
export TG_API_HASH=abcdef0123456789abcdef0123456789
```

### 3. 首次登录（生成 session）
```bash
python app.py login
# 按提示输入手机号、验证码（必要时两步验证密码）
```
成功后会生成 `tg_profile.session`，之后无需再登录。

### 4. 运行
```bash
python app.py run          # 前台运行
python app.py menu         # 交互菜单：切换模式 / 改前缀 / 改间隔 / 改参数 / 实时预览
```

`setup` 向导与 `menu` 交互菜单都基于 [rich](https://github.com/Textualize/rich) 渲染，在 Debian/Ubuntu 终端下有彩色分区、表格化的模式列表和输入校验（api_id/api_hash/时区非法会当场提示重填，不会写坏配置）。`menu` 里新增：

- **m 编辑当前模式参数**：直接改 `weather` 的经纬度、`crypto` 的币种、`countdown` 的目标日期等，无需手动改 JSON。
- **c 控制面板设置**：改触发表情 / 命令前缀 / 生效对话 / 启停，不用再手动改 `config.json` 的 `control` 段。
- **v 预览当前效果**：立即按当前配置渲染一次昵称，改完参数直接看到实际效果，出错也会用中文提示。
- **x 不保存退出**：改错了可以直接放弃，不会污染 `config.json`。

---

## 部署为 systemd 服务（VPS 常驻）

```bash
sudo bash install.sh        # 自动建 venv、装依赖、装服务到 /opt/tg-dynamic-profile
# 或手动：
sudo cp systemd/tg-profile.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now tg-profile
journalctl -u tg-profile -f   # 看实时日志
```

> ⚠️ systemd 是非交互的，**务必先在终端跑过 `python app.py login`** 生成 session，再启动服务。

---

## 配置说明（config.json）

```jsonc
{
  "api_id": 123456,
  "api_hash": "your_api_hash",
  "session": "tg_profile",        // session 文件名
  "mode": "time",                 // 当前生效的模式
  "prefix": "YourName",             // 名字主体
  "separator": " ",               // 前缀与内容之间的分隔符，可用 " | "、"｜"
  "timezone": "Europe/London",      // 时区
  "update_interval": 60,          // 刷新间隔（秒），建议 >= 60
  "modes": {                      // 各模式的参数
    "time":     { "format": "%H:%M" },
    "datetime": { "format": "%m/%d %H:%M" },
    "weekday":  { "lang": "zh" },
    "daynight": { "day_emoji": "☀️", "night_emoji": "🌙", "day_start": 6, "night_start": 18 },
    "weather":  { "lat": 51.5074, "lon": -0.1278, "cache_ttl": 1800 },
    "system":   { "format": "CPU {cpu:.0f}% RAM {ram:.0f}%" },
    "ping":     { "host": "1.1.1.1", "label": "HK" },
    "crypto":   { "symbol": "BTC", "vs": "usd", "cache_ttl": 120 },
    "countdown":{ "target": "2027-01-01", "label": "NewYear" },
    "holiday":  { "dates": { "01-01": "🎆", "12-25": "🎄", "10-31": "🎃" } },
    "custom":   { "template": "{prefix} {time}" }
  }
}
```

切换模式只需改 `"mode"` 字段（或用 `python app.py menu`），无需改代码。

---

## 自己加一个模式

在 `tgprofile/providers/builtin.py` 末尾：

```python
@provider("stars")
async def mode_stars(ctx):
    async def fetch():
        async with httpx.AsyncClient(timeout=10) as c:
            r = await c.get("https://api.github.com/repos/owner/repo")
            return r.json()["stargazers_count"]
    n = await cached("stars", 3600, fetch)   # 1 小时缓存
    return ctx.compose(f"⭐{n}")
```

然后 `"mode": "stars"` 即可。`ctx.compose(s)` = `prefix + separator + s`；想完全自定义就直接返回字符串。

---

## 常见问题

- **没反应？** 名字只在内容变化时更新；`time` 模式分钟变了才会改。看 `journalctl -u tg-profile -f`。
- **FloodWait？** 把 `update_interval` 调大（120/300）。日志会显示需等待秒数并自动退避。
- **想停止？** `systemctl stop tg-profile`，或菜单选「停止」。

## License
MIT
