"""Shared Rich 终端 UI 组件：让各交互界面（setup 向导 / menu 面板）风格统一、色彩清晰。"""
from rich.console import Console
from rich.panel import Panel

console = Console()


def banner(title, subtitle=None):
    text = f"[bold cyan]{title}[/bold cyan]"
    if subtitle:
        text += f"\n[dim]{subtitle}[/dim]"
    console.print(Panel.fit(text, border_style="cyan", padding=(0, 2)))


def section(title):
    console.print()
    console.rule(f"[bold]{title}[/bold]", style="cyan")


def ok(msg):
    console.print(f"[bold green]✅ {msg}[/bold green]")


def warn(msg):
    console.print(f"[bold yellow]⚠️  {msg}[/bold yellow]")


def err(msg):
    console.print(f"[bold red]❌ {msg}[/bold red]")


def info(msg):
    console.print(f"[cyan]ℹ️  {msg}[/cyan]")
