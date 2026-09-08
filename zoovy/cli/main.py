import argparse
import sys
import shutil
import io
import os

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, DownloadColumn

from zoovy.core.hardware import get_hardware_profile
from zoovy.core.llm import OllamaClient
from zoovy.agents.delivery.agent import DeliveryAgent

console = Console(highlight=False)


def print_banner():
    console.print("""[bold cyan]
███████╗ ██████╗  ██████╗ ██╗   ██╗██╗   ██╗
╚══███╔╝██╔═══██╗██╔═══██╗██║   ██║╚██╗ ██╔╝
  ███╔╝ ██║   ██║██║   ██║██║   ██║ ╚████╔╝ 
 ███╔╝  ██║   ██║██║   ██║╚██╗ ██╔╝  ╚██╔╝  
███████╗╚██████╔╝╚██████╔╝ ╚████╔╝    ██║   
╚══════╝ ╚═════╝  ╚═════╝   ╚═══╝     ╚═╝   
[/bold cyan][dim]Local Autonomous AI Agent Hub for Real-World Tasks[/dim]\n""")


def cmd_doctor(args):
    """Run comprehensive system health and hardware diagnostics."""
    print_banner()
    console.print("[bold]🔍 Running Zoovy System Diagnostic...[/bold]\n")

    profile = get_hardware_profile()

    # Hardware Table
    hw_table = Table(title="Hardware & VRAM Profile", expand=True)
    hw_table.add_column("Component", style="cyan", width=20)
    hw_table.add_column("Detected Value", style="green")
    hw_table.add_row("GPU Device", profile.gpu_name)
    hw_table.add_row("Dedicated VRAM", f"{profile.vram_gb:.1f} GB")
    hw_table.add_row("System RAM", f"{profile.system_ram_gb:.1f} GB")
    hw_table.add_row("CPU Cores", str(profile.cpu_cores))
    hw_table.add_row("Hardware Tier", profile.tier)
    hw_table.add_row("Recommended LLM", f"[bold yellow]{profile.recommended_model}[/bold yellow]")
    console.print(hw_table)

    console.print(Panel(profile.rationale, title="AI Engine Optimization Rationale", border_style="blue"))

    # Runtimes Table
    rt_table = Table(title="Runtime Environment Status", expand=True)
    rt_table.add_column("Service", style="cyan", width=20)
    rt_table.add_column("Status", style="white")

    ollama = OllamaClient()
    ollama_alive = ollama.is_alive()
    rt_table.add_row("Ollama Daemon", "[bold green]ONLINE (http://localhost:11434)[/bold green]" if ollama_alive else "[bold red]OFFLINE (Start via 'ollama serve')[/bold red]")

    if ollama_alive:
        installed = ollama.list_installed_models()
        model_ready = any(profile.recommended_model in m for m in installed)
        rt_table.add_row(f"Model '{profile.recommended_model}'", "[bold green]INSTALLED[/bold green]" if model_ready else "[bold yellow]NOT PULLED (Run 'zoovy setup')[/bold yellow]")

    from pathlib import Path
    standard_git_paths = [
        r"C:\Program Files\Git\cmd",
        os.path.expandvars(r"%LOCALAPPDATA%\Programs\Git\cmd"),
        r"C:\Program Files\Git\bin",
    ]
    git_found = shutil.which("git") is not None or any((Path(p) / "git.exe").exists() for p in standard_git_paths)
    rt_table.add_row("Git CLI", "[bold green]AVAILABLE[/bold green]" if git_found else "[bold red]NOT FOUND[/bold red]")

    console.print(rt_table)


def cmd_setup(args):
    """Auto-configure the recommended model and verify dependencies."""
    print_banner()
    profile = get_hardware_profile()
    console.print(f"[bold]Detected Configuration:[/bold] {profile.tier}")
    console.print(f"[bold]Optimal Target Model:[/bold] [cyan]{profile.recommended_model}[/cyan]\n")

    ollama = OllamaClient()
    if not ollama.is_alive():
        console.print("[bold red]Error:[/bold red] Ollama daemon is not running. Please start Ollama first.")
        sys.exit(1)

    if ollama.is_model_installed(profile.recommended_model):
        console.print(f"[bold green]✓ Model '{profile.recommended_model}' is already downloaded and ready to run.[/bold green]")
        return

    console.print(f"Pulling model [bold cyan]{profile.recommended_model}[/bold cyan] from Ollama registry...")
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        DownloadColumn(),
        console=console
    ) as progress:
        task = progress.add_task(f"Downloading {profile.recommended_model}...", total=None)
        for update in ollama.pull_model(profile.recommended_model):
            status = update.get("status", "")
            completed = update.get("completed", 0)
            total = update.get("total", 0)
            if total > 0:
                progress.update(task, total=total, completed=completed, description=status)
            else:
                progress.update(task, description=status)

    console.print(f"[bold green]✓ Setup complete! Model '{profile.recommended_model}' is ready.[/bold green]")


def cmd_login(args):
    """Open persistent browser for user to log in and save session credentials."""
    print_banner()
    platform = args.platform
    console.print(f"[bold cyan]🔑 Opening session for {platform.upper()}...[/bold cyan]")
    console.print("[dim]Log in once using your mobile number & OTP. Your session cookies and addresses will be saved locally.[/dim]\n")

    from zoovy.agents.delivery.browser import BrowserSessionManager
    from zoovy.agents.delivery.platforms.zepto import ZeptoDriver
    from zoovy.agents.delivery.platforms.swiggy import SwiggyDriver
    from zoovy.agents.delivery.platforms.zomato import ZomatoDriver

    session = BrowserSessionManager(platform_name=platform, headless=False)
    try:
        page = session.start()
        if platform == "zepto":
            driver = ZeptoDriver(page)
        elif platform == "swiggy":
            driver = SwiggyDriver(page)
        else:
            driver = ZomatoDriver(page)

        driver.navigate_home()
        console.print("[bold yellow]Please complete login and verify your delivery address in the opened browser window.[/bold yellow]")
        input("\nPress [Enter] once you are logged in and can see your profile/addresses...")

        saved_addrs = driver.get_saved_addresses()
        console.print(f"\n[bold green]✓ Session saved successfully for {platform.upper()}![/bold green]")
        console.print(f"Found {len(saved_addrs)} saved delivery address(es) on this account:")
        for a in saved_addrs:
            console.print(f"  • {a}")
    finally:
        session.close()
        console.print("\n[dim]Browser session safely closed and persisted.[/dim]")


def cmd_order(args):
    """Execute an autonomous delivery order."""
    print_banner()
    ollama = OllamaClient()
    if not ollama.is_alive():
        console.print("[bold red]Error:[/bold red] Ollama daemon is not reachable. Start Ollama and try again.")
        sys.exit(1)

    profile = get_hardware_profile()
    model = args.model or profile.recommended_model
    ollama.model = model

    agent = DeliveryAgent(llm_client=ollama)
    agent.execute_order(prompt=args.prompt, platform_override=args.platform)


def main():
    parser = argparse.ArgumentParser(description="Zoovy: Local Autonomous AI Agent Ecosystem")
    subparsers = parser.add_subparsers(dest="command", help="Subcommands")

    # doctor
    subparsers.add_parser("doctor", help="Check system hardware, VRAM, and runtime health")

    # setup
    subparsers.add_parser("setup", help="Auto-detect VRAM and download recommended LLM")

    # login
    login_parser = subparsers.add_parser("login", help="Log into a delivery platform (saves OTP session locally)")
    login_parser.add_argument("--platform", choices=["zepto", "swiggy", "zomato"], default="zepto", help="Target delivery platform (default: zepto)")

    # order
    order_parser = subparsers.add_parser("order", help="Execute autonomous delivery order")
    order_parser.add_argument("prompt", type=str, help="Natural language order prompt, e.g. 'Order 1kg tomatoes and Amul butter on Zepto'")
    order_parser.add_argument("--platform", choices=["zepto", "swiggy", "zomato"], help="Force specific delivery platform")
    order_parser.add_argument("--model", type=str, help="Override LLM model tag")

    args = parser.parse_args()
    if not args.command:
        parser.print_help()
        sys.exit(0)

    if args.command == "doctor":
        cmd_doctor(args)
    elif args.command == "setup":
        cmd_setup(args)
    elif args.command == "login":
        cmd_login(args)
    elif args.command == "order":
        cmd_order(args)


if __name__ == "__main__":
    main()
