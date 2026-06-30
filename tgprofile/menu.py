import json

from .config import load_config, save_config
from .providers import REGISTRY

MODE_DESC = {
    "time": "实时时间        YourName 09:15",
    "datetime": "日期 + 时间     YourName 06/30 09:15",
    "weekday": "星期            YourName 周二",
    "daynight": "昼夜切换        ☀️ YourName 09:15",
    "weather": "天气            YourName ☀️28°C",
    "system": "CPU/RAM        YourName CPU 12% RAM 43%",
    "ping": "延迟            YourName HK 23ms",
    "crypto": "币价            YourName BTC 108k",
    "countdown": "倒计时          YourName NewYear 156D",
    "holiday": "节日            🎄 YourName",
    "custom": "自定义模板      template 占位符",
}


def _load_raw(path):
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def menu(path):
    # load_config validates secrets; for menu we edit the raw file
    load_config(path)  # fail fast if api creds missing
    cfg = _load_raw(path)
    modes = sorted(REGISTRY)

    while True:
        print("\n" + "=" * 38)
        print(" Telegram Dynamic Profile")
        print("=" * 38)
        print(f" 当前: mode={cfg.get('mode')}  prefix={cfg.get('prefix')}"
              f"  interval={cfg.get('update_interval')}s\n")
        for i, m in enumerate(modes, 1):
            mark = "▶" if m == cfg.get("mode") else " "
            print(f" {mark}{i:>2}. {m:<10} {MODE_DESC.get(m, '')}")
        print("\n  p. 改前缀 prefix")
        print("  s. 改分隔符 separator")
        print("  i. 改刷新间隔 interval")
        print("  q. 保存并退出")

        choice = input("\n请选择: ").strip().lower()

        if choice == "q":
            save_config(path, cfg)
            print("已保存到", path)
            print("运行: python app.py run   （或重启 systemctl restart tg-profile）")
            return
        elif choice == "p":
            cfg["prefix"] = input("新前缀: ").strip()
        elif choice == "s":
            cfg["separator"] = input("新分隔符(例如 ' '、' | '、'｜'): ")
        elif choice == "i":
            try:
                cfg["update_interval"] = max(10, int(input("间隔(秒): ").strip()))
            except ValueError:
                print("无效数字")
        elif choice.isdigit() and 1 <= int(choice) <= len(modes):
            cfg["mode"] = modes[int(choice) - 1]
            print("已切换模式 ->", cfg["mode"])
        else:
            print("无效选择")
