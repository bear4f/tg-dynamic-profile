import asyncio
import json
from datetime import datetime
from zoneinfo import ZoneInfo

from rich.panel import Panel
from rich.prompt import IntPrompt, Prompt
from rich.table import Table

from .config import load_config, save_config
from .fonts import STYLE_LABELS, STYLE_ORDER, apply_style, is_known_style, normalize_style, style_example
from .providers import REGISTRY
from .ui import banner, console, err, info, ok, section, warn

MODE_DESC = {
    "time": ("实时时间", "{prefix}{sep}09:15"),
    "datetime": ("日期 + 时间", "{prefix}{sep}06/30 09:15"),
    "weekday": ("星期", "{prefix}{sep}周二"),
    "daynight": ("昼夜切换", "☀️ {prefix}{sep}09:15"),
    "weather": ("天气", "{prefix}{sep}☀️28°C"),
    "system": ("CPU/RAM", "{prefix}{sep}CPU 12% RAM 43%"),
    "ping": ("延迟", "{prefix}{sep}HK 23ms"),
    "crypto": ("币价", "{prefix}{sep}BTC 108k"),
    "countdown": ("倒计时", "{prefix}{sep}NewYear 156D"),
    "holiday": ("节日", "🎄 {prefix}"),
    "custom": ("自定义模板", "template 占位符"),
}


def _load_raw(path):
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def _valid_tz(tz):
    try:
        ZoneInfo(tz)
        return True
    except Exception:
        return False


def _parse_value(raw):
    """尽量按 JSON 解析（数字/布尔/字符串），失败则原样存为字符串。"""
    try:
        return json.loads(raw)
    except (json.JSONDecodeError, ValueError):
        return raw


def _trigger_display(ctrl):
    trig = ctrl.get("trigger", ["面板", "panel"])
    return " / ".join(trig) if isinstance(trig, (list, tuple)) else str(trig)


def _status_panel(cfg):
    ctrl = cfg.get("control") or {}
    lines = [
        f"模式 mode        [bold]{cfg.get('mode')}[/bold]",
        f"前缀 prefix      [bold]{cfg.get('prefix', '')}[/bold]",
        f"分隔符 separator '{cfg.get('separator', ' ')}'",
        f"字体 font        [bold]{normalize_style(cfg.get('font_style', 'plain'))}[/bold]",
        f"刷新间隔 interval {cfg.get('update_interval', 60)}s",
        f"时区 timezone    {cfg.get('timezone', 'UTC')}",
        f"控制面板         {'✅ 启用' if ctrl.get('enabled', True) else '⛔ 停用'}"
        f"（触发词 {_trigger_display(ctrl)} / 命令前缀 '{ctrl.get('prefix', '.')}'）",
    ]
    console.print(Panel("\n".join(lines), title="当前配置", border_style="blue", expand=False))


def _mode_table(cfg, modes):
    table = Table(title="可用模式（输入序号可直接切换）")
    table.add_column("序号", justify="right")
    table.add_column("模式")
    table.add_column("效果示例 / 说明")
    font_style = normalize_style(cfg.get("font_style", "plain"))
    prefix = cfg.get("prefix", "") or "YourName"
    sep = cfg.get("separator", " ")
    for i, m in enumerate(modes, 1):
        current = m == cfg.get("mode")
        mark = "▶" if current else " "
        style = "bold green" if current else None
        desc, template = MODE_DESC.get(m, ("", ""))
        sample = template.format(prefix=prefix, sep=sep)
        if m != "custom":
            sample = apply_style(sample, font_style)
        table.add_row(str(i), f"{mark} {m}", f"{desc}        {sample}", style=style)
    console.print(table)


def _edit_mode_params(cfg, mode):
    opts = cfg.setdefault("modes", {}).setdefault(mode, {})
    while True:
        console.print()
        keys = list(opts)
        if keys:
            table = Table(title=f"模式参数 · {mode}")
            table.add_column("序号", justify="right")
            table.add_column("参数名")
            table.add_column("当前值")
            for i, k in enumerate(keys, 1):
                table.add_row(str(i), k, json.dumps(opts[k], ensure_ascii=False))
            console.print(table)
        else:
            console.print(f"[dim](模式 '{mode}' 暂无参数，可新增)[/dim]")

        console.print("  输入序号修改参数   [bold]n[/bold]. 新增参数   [bold]b[/bold]. 返回上级菜单")
        choice = Prompt.ask("请选择").strip().lower()

        if choice == "b":
            return
        elif choice == "n":
            key = Prompt.ask("新参数名").strip()
            if not key:
                err("参数名不能为空")
                continue
            raw = Prompt.ask("参数值（支持 JSON，如数字/true/false，普通文本直接输入即可）")
            opts[key] = _parse_value(raw)
            ok(f"已新增 {key} = {opts[key]!r}")
        elif choice.isdigit() and 1 <= int(choice) <= len(keys):
            k = keys[int(choice) - 1]
            raw = Prompt.ask(f"{k} 新值（回车保持不变）",
                              default=json.dumps(opts[k], ensure_ascii=False))
            opts[k] = _parse_value(raw)
            ok(f"{k} → {opts[k]!r}")
        else:
            err("无效选择")


def _edit_control(cfg):
    ctrl = cfg.setdefault("control", {"enabled": True, "trigger": ["面板", "panel"],
                                       "prefix": ".", "chat": "me"})
    while True:
        console.print()
        console.print(Panel(
            f"启用状态   {'✅ 启用' if ctrl.get('enabled', True) else '⛔ 停用'}\n"
            f"触发词     {_trigger_display(ctrl)}\n"
            f"命令前缀   {ctrl.get('prefix', '.')}\n"
            f"生效对话   {ctrl.get('chat', 'me')}（me = 收藏夹，只识别你本人发出的消息）",
            title="控制面板设置", border_style="magenta"))
        console.print(
            "  1. 切换启用/停用   2. 改触发词   3. 改命令前缀   4. 改生效对话   b. 返回")
        choice = Prompt.ask("请选择").strip().lower()

        if choice == "b":
            return
        elif choice == "1":
            ctrl["enabled"] = not ctrl.get("enabled", True)
            ok("已切换" if ctrl["enabled"] else "已停用")
        elif choice == "2":
            raw = Prompt.ask("新触发词（不区分大小写；支持中/英文/表情；多个用逗号分隔，如 面板,panel）",
                              default=_trigger_display(ctrl).replace(" / ", ","))
            parts = [p.strip() for p in raw.split(",") if p.strip()]
            if not parts:
                err("触发词不能为空")
            else:
                ctrl["trigger"] = parts[0] if len(parts) == 1 else parts
                ok(f"触发词 → {_trigger_display(ctrl)}")
        elif choice == "3":
            ctrl["prefix"] = Prompt.ask("新命令前缀", default=ctrl.get("prefix", "."))
        elif choice == "4":
            ctrl["chat"] = Prompt.ask("新生效对话（默认 me = 收藏夹）", default=ctrl.get("chat", "me"))
        else:
            err("无效选择")


def _edit_font_style(cfg):
    while True:
        table = Table(title="字体样式（会转换前缀和后面的时间/数字）")
        table.add_column("序号", justify="right")
        table.add_column("名称")
        table.add_column("效果")
        current = normalize_style(cfg.get("font_style", "plain"))
        for i, style in enumerate(STYLE_ORDER, 1):
            mark = "▶" if style == current else " "
            style_name = f"{mark} {style}"
            row_style = "bold green" if style == current else None
            table.add_row(str(i), style_name, STYLE_LABELS[style], style=row_style)
        console.print(table)
        console.print("  输入序号/样式名切换字体   [bold]b[/bold]. 返回主面板")
        choice = Prompt.ask("请选择", default=current).strip().lower()
        if choice == "b":
            return
        if choice.isdigit() and 1 <= int(choice) <= len(STYLE_ORDER):
            selected = STYLE_ORDER[int(choice) - 1]
        else:
            if not is_known_style(choice):
                err(f"未知字体样式: {choice}，可用: {', '.join(STYLE_ORDER)}")
                continue
            selected = normalize_style(choice)
        cfg["font_style"] = selected
        ok(f"字体 → {selected}，示例：{style_example(selected)}")
        return


def _preview(cfg):
    mode = cfg.get("mode")
    fn = REGISTRY.get(mode)
    if fn is None:
        err(f"未知模式: {mode}")
        return

    tz = cfg.get("timezone", "UTC")
    if not _valid_tz(tz):
        warn(f"时区 '{tz}' 无效，已用 UTC 预览")
        tz = "UTC"
    now = datetime.now(ZoneInfo(tz))

    from .runner import Ctx  # 延迟导入，避免 menu 无关命令也加载 telethon
    opts = cfg.get("modes", {}).get(mode, {})
    ctx = Ctx(
        now,
        cfg.get("prefix", ""),
        cfg.get("separator", " "),
        opts,
        normalize_style(cfg.get("font_style", "plain")),
    )
    try:
        name = apply_style(asyncio.run(fn(ctx)), ctx.font_style)
        console.print(Panel(f"[bold green]{name}[/bold green]",
                             title="预览效果（当前会实际显示的昵称）", border_style="green"))
    except Exception as e:
        err(f"预览失败: {e}")


def menu(path):
    # load_config validates secrets; for menu we edit the raw file
    load_config(path)  # fail fast if api creds missing
    cfg = _load_raw(path)
    modes = sorted(REGISTRY)

    banner("Telegram Dynamic Profile · 控制菜单", "改动仅在选择『保存并退出』时写入 config.json")

    while True:
        section("当前状态")
        _status_panel(cfg)
        _mode_table(cfg, modes)
        console.print(
            "\n"
            "  [bold]p[/bold]. 改前缀 prefix        [bold]s[/bold]. 改分隔符 separator\n"
            "  [bold]f[/bold]. 改字体 font          [bold]i[/bold]. 改刷新间隔 interval\n"
            "  [bold]t[/bold]. 改时区 timezone      [bold]m[/bold]. 编辑当前模式参数\n"
            "  [bold]c[/bold]. 控制面板设置\n"
            "  [bold]v[/bold]. 预览当前效果          [bold]q[/bold]. 保存并退出\n"
            "                                    [bold]x[/bold]. 不保存退出\n"
        )

        choice = Prompt.ask("请选择").strip().lower()

        if choice == "q":
            save_config(path, cfg)
            ok(f"已保存到 {path}")
            info("正在运行的 app.py run 会在几秒内自动生效，无需手动重启")
            return
        elif choice == "x":
            warn("已放弃修改，未保存")
            return
        elif choice == "p":
            cfg["prefix"] = Prompt.ask("新前缀", default=cfg.get("prefix", ""))
        elif choice == "s":
            cfg["separator"] = Prompt.ask("新分隔符（例如空格、' | '、'｜'）",
                                          default=cfg.get("separator", " "))
        elif choice == "f":
            _edit_font_style(cfg)
        elif choice == "i":
            cfg["update_interval"] = max(10, IntPrompt.ask(
                "刷新间隔（秒，最小 10，建议 ≥60 避免限流）",
                default=cfg.get("update_interval", 60)))
        elif choice == "t":
            tz = Prompt.ask("新时区（如 Asia/Shanghai）", default=cfg.get("timezone", "UTC"))
            if _valid_tz(tz):
                cfg["timezone"] = tz
                ok(f"时区 → {tz}")
            else:
                err(f"无效时区: {tz}")
        elif choice == "m":
            _edit_mode_params(cfg, cfg.get("mode"))
        elif choice == "c":
            _edit_control(cfg)
        elif choice == "v":
            _preview(cfg)
        elif choice.isdigit() and 1 <= int(choice) <= len(modes):
            cfg["mode"] = modes[int(choice) - 1]
            ok(f"已切换模式 → {cfg['mode']}")
        else:
            err("无效选择")
