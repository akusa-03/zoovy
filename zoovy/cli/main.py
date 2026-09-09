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
from zoovy.core.llm import OllamaClient, ensure_ollama_running
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
    hw_table.add_row("Default Model", f"[bold green]{profile.default_model}[/bold green] (Ultra-fast, ~986MB)")
    hw_table.add_row("Enhanced Model", f"[bold yellow]{profile.enhanced_model}[/bold yellow] (Hardware-Optimized)")
    console.print(hw_table)

    console.print(Panel(profile.rationale, title="AI Engine Optimization Rationale", border_style="blue"))

    # Runtimes Table
    rt_table = Table(title="Runtime Environment Status", expand=True)
    rt_table.add_column("Service", style="cyan", width=20)
    rt_table.add_column("Status", style="white")

    ollama = OllamaClient()
    ollama_alive = ensure_ollama_running()
    rt_table.add_row("Ollama Daemon", "[bold green]ONLINE (http://localhost:11434)[/bold green]" if ollama_alive else "[bold red]OFFLINE (Start via 'ollama serve')[/bold red]")

    if ollama_alive:
        installed = ollama.list_installed_models()
        default_ready = any(profile.default_model in m for m in installed)
        enhanced_ready = any(profile.enhanced_model in m for m in installed)
        rt_table.add_row(f"Default '{profile.default_model}'", "[bold green]INSTALLED[/bold green]" if default_ready else "[bold yellow]NOT PULLED (Run 'zoovy setup')[/bold yellow]")
        rt_table.add_row(f"Enhanced '{profile.enhanced_model}'", "[bold green]INSTALLED[/bold green]" if enhanced_ready else "[dim]Optional (Run 'zoovy setup')[/dim]")

    from pathlib import Path
    standard_git_paths = [
        r"C:\Program Files\Git\cmd",
        os.path.expandvars(r"%LOCALAPPDATA%\Programs\Git\cmd"),
        r"C:\Program Files\Git\bin",
    ]
    git_found = shutil.which("git") is not None or any((Path(p) / "git.exe").exists() for p in standard_git_paths)
    rt_table.add_row("Git CLI", "[bold green]AVAILABLE[/bold green]" if git_found else "[bold red]NOT FOUND[/bold red]")

    # MCP Engine Status
    rt_table.add_row("Core Engine", "[bold green]Zero-Browser MCP (Fast JSON-RPC API)[/bold green]")
    rt_table.add_row("MCP Providers", "[bold green]Zepto, Swiggy, Zomato MCP Active[/bold green]")

    # Browser Fallback Status
    try:
        import playwright
        rt_table.add_row("Browser Engine", "[cyan]Playwright Installed (Optional Fallback)[/cyan]")
    except ImportError:
        rt_table.add_row("Browser Engine", "[dim]Stashed (Zero-Browser MCP is active default)[/dim]")

    console.print(rt_table)


def cmd_setup(args):
    """Auto-configure the recommended model and verify dependencies."""
    print_banner()
    profile = get_hardware_profile()
    console.print(f"[bold]Detected Hardware:[/bold] {profile.gpu_name} ({profile.vram_gb:.1f} GB VRAM) - {profile.tier}")

    ollama = OllamaClient()
    if not ensure_ollama_running():
        console.print("[bold red]Error:[/bold red] Ollama daemon could not be reached or started. Please install Ollama from https://ollama.com.")
        sys.exit(1)

    # Determine target model
    target_model = args.model
    if not target_model:
        console.print("\n[bold cyan]Choose AI Model Tier to Install:[/bold cyan]")
        console.print(f"  [bold green][1] {profile.default_model}[/bold green] [bold](Default)[/bold] - Ultra-fast, lightweight (~986 MB), instant setup")
        console.print(f"  [yellow][2] {profile.enhanced_model}[/yellow] - Enhanced Model (Optimized for your {profile.gpu_name}, {profile.vram_gb:.1f}GB VRAM)")
        console.print(f"  [white][3] qwen2.5:7b[/white] - Balanced Model (~5.2 GB)")
        console.print(f"  [white][4] qwen2.5:3b[/white] - Standard Lightweight (~2.6 GB)")

        try:
            choice = input(f"\nSelect model [1-4, Default: 1 ({profile.default_model})]: ").strip()
        except (KeyboardInterrupt, EOFError):
            choice = "1"

        if choice == "2":
            target_model = profile.enhanced_model
        elif choice == "3":
            target_model = "qwen2.5:7b"
        elif choice == "4":
            target_model = "qwen2.5:3b"
        else:
            target_model = profile.default_model

    console.print(f"\n[green]✓ Selected Model:[/green] [bold cyan]{target_model}[/bold cyan]\n")
    if ollama.is_model_installed(target_model):
        console.print(f"[bold green]✓ Model '{target_model}' is already downloaded and ready to run.[/bold green]")
        return

    console.print(f"Pulling model [bold cyan]{target_model}[/bold cyan] from Ollama registry...")
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        DownloadColumn(),
        console=console
    ) as progress:
        task = progress.add_task(f"Downloading {target_model}...", total=None)
        for update in ollama.pull_model(target_model):
            status = update.get("status", "")
            completed = update.get("completed", 0)
            total = update.get("total", 0)
            if total > 0:
                progress.update(task, total=total, completed=completed, description=status)
            else:
                progress.update(task, description=status)

    console.print(f"[bold green]✓ Setup complete! Model '{target_model}' is ready.[/bold green]")


def cmd_login(args):
    """Log into a delivery platform (via MCP token or optional browser session)."""
    print_banner()
    platform = args.platform.lower()
    console.print(f"[bold cyan]🔑 Account Session Login for {platform.upper()}[/bold cyan]\n")

    # If user explicitly requested browser-based OTP login
    if args.browser:
        try:
            from zoovy.agents.delivery.browser import BrowserSessionManager
            from zoovy.agents.delivery.platforms.zepto import ZeptoDriver
            from zoovy.agents.delivery.platforms.swiggy import SwiggyDriver
            from zoovy.agents.delivery.platforms.zomato import ZomatoDriver
        except ImportError:
            console.print("[bold red]Error: Playwright browser engine is not installed.[/bold red]")
            console.print("To use browser-based OTP login, install the optional browser extra:")
            console.print("  [bold cyan]pip install -e \".[browser]\"[/bold cyan]")
            console.print("  [bold cyan]playwright install chromium[/bold cyan]\n")
            console.print("[dim]Or run 'zoovy login' without --browser for fast Zero-Browser MCP token setup.[/dim]")
            return

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
            if saved_addrs:
                from zoovy.core.address_book import AddressBook
                AddressBook.sync_external_addresses(saved_addrs)
                console.print(f"Synced {len(saved_addrs)} saved delivery address(es) into ~/.zoovy/addresses.yaml:")
                for a in saved_addrs:
                    console.print(f"  • {a}")
        finally:
            session.close()
            console.print("\n[dim]Browser session safely closed and persisted.[/dim]")
        return

    # Zero-Browser MCP Mode Login (Default)
    token_input = args.token
    if not token_input:
        console.print("[bold]⚡ Zero-Browser MCP Account Link[/bold]")
        console.print(f"Link your {platform.title()} session token to automatically fetch your saved cloud addresses.")
        console.print("[dim]Tip: You can get your session token/JWT from your browser DevTools (Network tab -> Authorization header)[/dim]\n")
        try:
            token_input = input(f"Enter {platform.title()} Session / Auth Token (or press [Enter] to skip): ").strip()
        except (KeyboardInterrupt, EOFError):
            return

    if token_input:
        from zoovy.core.mcp_client import SwiggyMCPClient, ZeptoMCPClient, ZomatoMCPClient
        client = (
            SwiggyMCPClient() if platform == "swiggy"
            else ZeptoMCPClient() if platform == "zepto"
            else ZomatoMCPClient()
        )
        client.save_token({"access_token": token_input, "platform": platform})
        console.print(f"\n[bold green]✓ Successfully linked {platform.upper()} account![/bold green]")
        console.print(f"[dim]Stored locally in {client.token_file}[/dim]")

        # Fetch cloud addresses
        cloud_addrs = client.get_saved_addresses()
        if cloud_addrs:
            console.print(f"\n[bold green]✓ Synced {len(cloud_addrs)} delivery address(es) from your account:[/bold green]")
            for a in cloud_addrs:
                console.print(f"  • {a}")
    else:
        from zoovy.core.address_book import AddressBook
        addrs = AddressBook.load_addresses()
        if addrs:
            console.print(f"[green]Using your local AddressBook ({len(addrs)} address(es) in ~/.zoovy/addresses.yaml):[/green]")
            for lbl, addr in addrs.items():
                console.print(f"  • [cyan]{lbl}[/cyan]: {addr}")
        else:
            console.print("\n[dim]No token entered. Zoovy will use your local address book.[/dim]")
            console.print("[dim]Run 'zoovy address add \"<address>\" --label Home' to save your delivery location manually.[/dim]")


def cmd_order(args):
    """Execute an autonomous delivery order."""
    print_banner()
    ollama = OllamaClient()
    if not ensure_ollama_running():
        console.print("[bold red]Error:[/bold red] Ollama daemon could not be reached or started. Please install Ollama from https://ollama.com.")
        sys.exit(1)

    profile = get_hardware_profile()
    model = args.model or profile.default_model
    ollama.model = model

    agent = DeliveryAgent(llm_client=ollama)
    agent.execute_order(prompt=args.prompt, platform_override=args.platform, use_browser=args.browser)


def cmd_metadata(args):
    """View and manage Swiggy user metadata and addresses stored in JSON."""
    from zoovy.agents.delivery.swiggy_metadata import SwiggyMetadataAgent
    agent = SwiggyMetadataAgent()
    action = getattr(args, "action", "list") or "list"

    if action == "list":
        agent.display_metadata_summary()
    elif action == "add":
        tag = getattr(args, "tag", None) or "Home"
        agent.ask_and_store_address(tag=tag)
    elif action == "sync":
        meta = agent.load_metadata()
        console.print(f"[bold green]✓ Synced {len(meta.get('addresses', {}))} address(es) from {agent.metadata_file}[/bold green]")


def cmd_address(args):
    """View and manage real delivery addresses saved locally."""
    from zoovy.core.address_book import AddressBook
    from zoovy.agents.delivery.swiggy_metadata import SwiggyMetadataAgent
    metadata_agent = SwiggyMetadataAgent()
    action = args.action or "list"

    if action == "list":
        addresses = AddressBook.load_addresses()
        meta_addrs = metadata_agent.get_addresses()
        if not addresses and not meta_addrs:
            console.print("[yellow]No delivery addresses saved yet in ~/.zoovy/swiggy_metadata.json.[/yellow]")
            console.print("[dim]Run 'zoovy address add \"Flat 302, Palm Grove, Powai, Mumbai - 400076\" --label Home' to add one.[/dim]")
            return

        table = Table(title="📍 Saved Delivery Addresses (Swiggy Metadata & AddressBook)", expand=True)
        table.add_column("Label", style="cyan bold", width=15)
        table.add_column("Delivery Address", style="white")
        table.add_column("Source", style="green", width=15)

        for lbl, info in meta_addrs.items():
            table.add_row(lbl, info.get("formatted", ""), "JSON Metadata")
        for lbl, addr in addresses.items():
            if lbl not in meta_addrs:
                table.add_row(lbl, addr, "YAML Book")
        console.print(table)

    elif action == "add":
        if not args.address_text:
            console.print("[bold red]Error:[/bold red] Please provide the delivery address text.")
            console.print("[dim]Usage: zoovy address add \"Flat 302, Palm Grove, Powai, Mumbai - 400076\" --label Home[/dim]")
            return
        label = args.label or "Home"
        AddressBook.save_address(label, args.address_text)
        # Also store in Swiggy metadata JSON
        meta = metadata_agent.load_metadata()
        meta["addresses"][label] = {
            "tag": label,
            "formatted": args.address_text,
            "city": "Bengaluru",
            "pincode": "560066"
        }
        metadata_agent.save_metadata(meta)
        console.print(f"[bold green]✓ Address saved under label '[cyan]{label}[/cyan]':[/bold green] {args.address_text}")
        console.print(f"[dim]Stored locally in {metadata_agent.metadata_file} and {AddressBook.FILE_PATH}[/dim]")

    elif action == "remove":
        label = args.label or (args.address_text if args.address_text else None)
        if not label:
            console.print("[bold red]Error:[/bold red] Please specify the label to remove (e.g. 'zoovy address remove Home').")
            return
        removed_yaml = AddressBook.remove_address(label)
        meta = metadata_agent.load_metadata()
        removed_json = False
        if label in meta.get("addresses", {}):
            del meta["addresses"][label]
            metadata_agent.save_metadata(meta)
            removed_json = True

        if removed_yaml or removed_json:
            console.print(f"[bold green]✓ Successfully removed address '[cyan]{label}[/cyan]'.[/bold green]")
        else:
            console.print(f"[yellow]No address found with label '{label}'.[/yellow]")


def cmd_kill(args):
    """Emergency kill switch: terminate all background processes and unlock resources."""
    print_banner()
    console.print("[bold red]🛑 Activating Zoovy Emergency Kill Switch...[/bold red]\n")
    import psutil
    from pathlib import Path

    my_pids = {os.getpid()}
    if hasattr(os, "getppid"):
        my_pids.add(os.getppid())

    killed = 0
    for p in psutil.process_iter(['pid', 'name', 'cmdline']):
        try:
            if p.pid in my_pids:
                continue
            cmd = " ".join(p.info['cmdline'] or []).lower()
            name = (p.info['name'] or "").lower()

            # Skip the current kill command invocation
            if "kill" in cmd or "clean" in cmd:
                continue

            should_kill = False
            if ("python" in name or "pip" in name) and "zoovy" in cmd:
                should_kill = True
            elif ("chromium" in name or "playwright" in name or "node" in name) and "zoovy" in cmd:
                should_kill = True
            elif "ollama" in name and "serve" in cmd:
                should_kill = True

            if should_kill:
                console.print(f"  [yellow]• Terminating {name} (PID: {p.pid})...[/yellow]")
                p.kill()
                killed += 1
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            pass

    if killed == 0:
        console.print("  [green]✓ No active locking background processes found.[/green]")
    else:
        console.print(f"\n[bold green]✓ Terminated {killed} background process(es). All directory locks released.[/bold green]")

    if args.purge_config:
        config_dir = Path.home() / ".zoovy"
        if config_dir.exists():
            shutil.rmtree(config_dir, ignore_errors=True)
            console.print(f"[bold green]✓ Purged configuration at {config_dir}[/bold green]")

    console.print("[dim]The Zoovy directory can now be safely edited, moved, or deleted.[/dim]\n")


def main():
    parser = argparse.ArgumentParser(description="Zoovy: Local Autonomous AI Agent Ecosystem")
    subparsers = parser.add_subparsers(dest="command", help="Subcommands")

    # doctor
    subparsers.add_parser("doctor", help="Check system hardware, VRAM, and runtime health")

    # setup
    setup_parser = subparsers.add_parser("setup", help="Auto-detect VRAM and download recommended LLM")
    setup_parser.add_argument("--model", type=str, help="Specify model tag to pull directly (e.g. 'qwen2.5:1.5b', 'qwen2.5:14b')")

    # login
    login_parser = subparsers.add_parser("login", help="Log into a delivery platform (MCP token or browser session)")
    login_parser.add_argument("--platform", choices=["zepto", "swiggy", "zomato"], default="swiggy", help="Target delivery platform (default: swiggy)")
    login_parser.add_argument("--token", type=str, help="Direct session auth token or API key for MCP mode")
    login_parser.add_argument("--browser", action="store_true", help="Launch visual browser OTP login instead of Zero-Browser MCP token")

    # address
    addr_parser = subparsers.add_parser("address", help="View or manage saved local delivery addresses")
    addr_parser.add_argument("action", nargs="?", choices=["list", "add", "remove"], default="list", help="Action (list, add, remove; default: list)")
    addr_parser.add_argument("address_text", nargs="?", type=str, help="Full address string to add, or label to remove")
    addr_parser.add_argument("--label", type=str, default="Home", help="Label for address (e.g. Home, Work, Parents; default: Home)")

    # metadata
    meta_parser = subparsers.add_parser("metadata", help="View or manage Swiggy user metadata and addresses stored in JSON")
    meta_parser.add_argument("action", nargs="?", choices=["list", "add", "sync"], default="list", help="Action (list, add, sync; default: list)")
    meta_parser.add_argument("--tag", type=str, default="Home", help="Tag for address (Home/Work/Other)")

    # kill / clean
    kill_parser = subparsers.add_parser("kill", aliases=["clean"], help="Emergency kill switch: terminate background processes and unlock folder")
    kill_parser.add_argument("--purge-config", action="store_true", help="Also purge ~/.zoovy (addresses, tokens, audit logs)")

    # order
    order_parser = subparsers.add_parser("order", help="Execute autonomous delivery order")
    order_parser.add_argument("prompt", type=str, help="Natural language order prompt, e.g. 'Order 1kg tomatoes and Amul butter on Zepto'")
    order_parser.add_argument("--platform", choices=["zepto", "swiggy", "swiggy_food", "swiggy_instamart", "zomato"], help="Force specific delivery platform")
    order_parser.add_argument("--model", type=str, help="Override LLM model tag")
    order_parser.add_argument("--browser", action="store_true", help="Launch Playwright browser fallback instead of default zero-browser MCP engine")

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
    elif args.command == "address":
        cmd_address(args)
    elif args.command == "metadata":
        cmd_metadata(args)
    elif args.command in ("kill", "clean"):
        cmd_kill(args)
    elif args.command == "order":
        cmd_order(args)


if __name__ == "__main__":
    main()
