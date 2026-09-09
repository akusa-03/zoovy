"""
Interactive Chat Box / REPL for Zoovy.
Provides a persistent terminal chat shell for conversational AI,
autonomous recipe research, and Swiggy Food & Instamart ordering via MCP.
"""

import sys
import os
import atexit
from pathlib import Path
from typing import Optional, List, Dict, Any

from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.text import Text
from rich.markdown import Markdown

from zoovy.core.hardware import get_hardware_profile
from zoovy.core.llm import OllamaClient, ensure_ollama_running
from zoovy.core.web_search import WebSearchEngine
from zoovy.agents.delivery.agent import DeliveryAgent
from zoovy.agents.delivery.swiggy_metadata import SwiggyMetadataAgent
from zoovy.core.address_book import AddressBook
from zoovy.core.mcp_client import SwiggyFoodMCPClient, SwiggyInstamartMCPClient

console = Console(highlight=False)


def setup_readline():
    """Configures persistent command history and arrow key navigation."""
    try:
        import readline
        history_file = Path.home() / ".zoovy" / "chat_history"
        history_file.parent.mkdir(parents=True, exist_ok=True)
        if history_file.exists():
            try:
                readline.read_history_file(str(history_file))
            except Exception:
                pass
        readline.set_history_length(1000)

        def _save():
            try:
                readline.write_history_file(str(history_file))
            except Exception:
                pass

        atexit.register(_save)
    except (ImportError, Exception):
        pass


def is_order_or_recipe_intent(prompt: str) -> bool:
    """Detects whether a prompt should be routed to the autonomous Delivery Agent."""
    p = prompt.lower()
    order_signals = [
        "order", "buy", "cart", "bring", "instamart", "swiggy", "zepto", "zomato",
        "add to cart", "add ingredients", "add item", "deliver", "delivery",
        "biryani", "pizza", "burger", "diet coke", "groceries", "pantry",
        "recipe and add", "ingredients to cart"
    ]
    return any(signal in p for signal in order_signals)


class InteractiveChatSession:
    """
    Stateful interactive chat shell managing conversations,
    agent dispatch, and tool shortcuts.
    """

    def __init__(self, model_name: Optional[str] = None):
        self.profile = get_hardware_profile()
        self.model_name = model_name or self.profile.default_model
        self.llm = OllamaClient(model=self.model_name)
        self.metadata_agent = SwiggyMetadataAgent()
        self.delivery_agent = DeliveryAgent(llm_client=self.llm)
        self.chat_history: List[Dict[str, str]] = [
            {
                "role": "system",
                "content": (
                    "You are Zoovy, a helpful local autonomous AI agent running directly on the user's machine. "
                    "You can research recipes, answer questions, and autonomously manage food and grocery orders "
                    "via Swiggy Food and Swiggy Instamart official MCP servers. Always be concise, helpful, and friendly."
                )
            }
        ]

    def render_welcome(self):
        """Prints the interactive shell header and active configurations."""
        header_text = (
            "[bold cyan]⚡ Zoovy Interactive AI Agent Shell[/bold cyan]\n"
            "[dim]Autonomous real-world actions, live web search, and official Swiggy MCP integration.[/dim]\n\n"
            f"• [bold]Model:[/bold] [cyan]{self.model_name}[/cyan] ({self.profile.gpu_name}, {self.profile.vram_gb:.1f}GB VRAM - {self.profile.tier})\n"
            f"• [bold]Primary Address:[/bold] [green]{self.metadata_agent.get_default_address()}[/green]\n"
            f"• [bold]MCP Providers:[/bold] [green]Swiggy Food, Swiggy Instamart, Zepto, Zomato[/green]\n"
            f"• [bold]Web Intelligence:[/bold] [green]Live Zero-API Web Search Active[/green]\n\n"
            "[dim]Type your recipe, grocery, or food request below. Type [bold cyan]/help[/bold cyan] for commands, [bold cyan]exit[/bold cyan] to quit.[/dim]"
        )
        console.print()
        console.print(Panel(header_text, title="🤖 Zoovy Agent REPL", border_style="cyan"))

    def show_help(self):
        """Displays interactive commands and example queries."""
        table = Table(title="Zoovy Chat Shell Commands & Examples", expand=True)
        table.add_column("Command / Action", style="bold cyan", width=24)
        table.add_column("Description", style="white")

        table.add_row("/help", "Show this command reference table")
        table.add_row("/address", "List and manage saved delivery addresses")
        table.add_row("/metadata", "Inspect Swiggy metadata JSON file")
        table.add_row("/cart", "View current items in your delivery cart")
        table.add_row("/doctor", "Run system hardware and runtime health check")
        table.add_row("/model [name]", "View or switch active local Ollama model")
        table.add_row("/clear", "Clear screen and redisplay status header")
        table.add_row("exit / quit", "Exit the interactive chat box")

        table.add_section()
        table.add_row(
            "[yellow]Recipe & Groceries[/yellow]",
            "e.g. 'Find a recipe for chicken biriyani and add ingredients to swiggy instamart cart'"
        )
        table.add_row(
            "[yellow]Dark Store Essentials[/yellow]",
            "e.g. 'Order 1kg fresh tomatoes and Amul butter on Instamart'"
        )
        table.add_row(
            "[yellow]Restaurant Food[/yellow]",
            "e.g. 'Order paneer butter masala and butter naan on Swiggy'"
        )
        table.add_row(
            "[yellow]General Questions[/yellow]",
            "e.g. 'How do I cook fluffy basmati rice?' or 'What are high protein vegetarian foods?'"
        )
        console.print(table)

    def show_cart(self):
        """Displays currently active items in MCP carts."""
        instamart_client = SwiggyInstamartMCPClient()
        food_client = SwiggyFoodMCPClient()

        im_cart = instamart_client.get_cart()
        fd_cart = food_client.get_cart()

        total_items = len(im_cart.get("items", [])) + len(fd_cart.get("items", []))
        if total_items == 0:
            console.print("[yellow]🛒 Your delivery carts are currently empty.[/yellow]")
            console.print("[dim]Ask Zoovy to add items, e.g. 'Add 2 cans of Diet Coke to Instamart cart'.[/dim]")
            return

        table = Table(title="🛒 Current Active Delivery Carts (MCP)", expand=True)
        table.add_column("Platform", style="cyan", width=16)
        table.add_column("Item Name", style="white")
        table.add_column("Qty", style="magenta", justify="center", width=8)
        table.add_column("Price (₹)", style="green", justify="right", width=12)

        for it in im_cart.get("items", []):
            table.add_row("Swiggy Instamart", it.get("name", "Item"), str(it.get("quantity", 1)), f"₹{it.get('total_price_inr', 0):.2f}")
        for it in fd_cart.get("items", []):
            table.add_row("Swiggy Food", it.get("name", "Dish"), str(it.get("quantity", 1)), f"₹{it.get('total_price_inr', 0):.2f}")

        console.print(table)

    def show_addresses(self, sub_args: str = ""):
        """Inspects and manages delivery addresses."""
        sub_args = sub_args.strip()
        if not sub_args or sub_args == "list":
            meta_addrs = self.metadata_agent.get_addresses()
            if not meta_addrs:
                console.print("[yellow]No addresses saved yet. Use '/address add <label> <address>' to add one.[/yellow]")
                return

            table = Table(title="📍 Saved Delivery Addresses (Swiggy Metadata JSON)", expand=True)
            table.add_column("Tag", style="bold cyan", width=12)
            table.add_column("Address", style="white")
            table.add_column("Pincode", style="green", width=12)

            for tag, info in meta_addrs.items():
                table.add_row(tag, info.get("formatted", ""), info.get("pincode", ""))
            console.print(table)
        elif sub_args.startswith("add "):
            text = sub_args[4:].strip()
            parts = text.split(" ", 1)
            if len(parts) == 2 and parts[0].lower() in ["home", "work", "other", "parents", "office"]:
                tag, addr = parts[0].capitalize(), parts[1]
            else:
                tag, addr = "Home", text
            AddressBook.save_address(tag, addr)
            meta = self.metadata_agent.load_metadata()
            meta["addresses"][tag] = {
                "tag": tag,
                "formatted": addr,
                "city": "Bengaluru",
                "pincode": "560066"
            }
            self.metadata_agent.save_metadata(meta)
            console.print(f"[bold green]✓ Saved address under '[cyan]{tag}[/cyan]':[/bold green] {addr}")
        else:
            console.print("[yellow]Usage: /address [list | add <Tag> <Full Address>][/yellow]")

    def handle_conversational_query(self, user_msg: str):
        """Responds conversationally using local LLM with web search context."""
        web_context = ""
        if any(w in user_msg.lower() for w in ["what", "how", "why", "when", "recipe", "who", "latest", "news"]):
            try:
                search_res = WebSearchEngine.enrich_query_context(user_msg, max_results=3)
                web_context = search_res.get("context_summary", "")
            except Exception:
                pass

        full_prompt = user_msg
        if web_context:
            full_prompt += f"\n\n[Web Context Reference:\n{web_context}]"

        self.chat_history.append({"role": "user", "content": full_prompt})

        console.print("\n[dim]Thinking...[/dim]")
        try:
            response_text = self.llm.chat(self.chat_history)
            self.chat_history.append({"role": "assistant", "content": response_text})
            console.print(Panel(Markdown(response_text), title="💬 Zoovy Assistant", border_style="green"))
        except Exception as e:
            console.print(f"[bold red]LLM Error:[/bold red] {e}")

    def run_loop(self):
        """Main REPL loop."""
        setup_readline()
        self.render_welcome()

        while True:
            try:
                console.print()
                user_input = console.input("[bold cyan]zoovy ❯ [/bold cyan]").strip()
            except (KeyboardInterrupt, EOFError):
                console.print("\n[bold yellow]Exiting Zoovy Shell. Goodbye![/bold yellow]")
                break

            if not user_input:
                continue

            # Command routing
            cmd_lower = user_input.lower()
            if cmd_lower in ["exit", "quit", "/exit", "/quit", ":q"]:
                console.print("[bold yellow]Exiting Zoovy Shell. Goodbye![/bold yellow]")
                break
            elif cmd_lower in ["/help", "help"]:
                self.show_help()
                continue
            elif cmd_lower in ["/cart", "cart"]:
                self.show_cart()
                continue
            elif cmd_lower.startswith("/address"):
                sub = user_input[8:].strip()
                self.show_addresses(sub)
                continue
            elif cmd_lower in ["/metadata", "metadata"]:
                self.metadata_agent.display_metadata_summary()
                continue
            elif cmd_lower in ["/clear", "clear"]:
                os.system("clear" if os.name != "nt" else "cls")
                self.render_welcome()
                continue
            elif cmd_lower in ["/doctor", "doctor"]:
                from zoovy.cli.main import cmd_doctor
                class DummyArgs:
                    pass
                cmd_doctor(DummyArgs())
                continue
            elif cmd_lower.startswith("/model"):
                parts = user_input.split(maxsplit=1)
                if len(parts) > 1:
                    new_model = parts[1].strip()
                    self.model_name = new_model
                    self.llm.model = new_model
                    console.print(f"[bold green]✓ Switched active model to:[/bold green] [cyan]{new_model}[/cyan]")
                else:
                    console.print(f"[bold]Current model:[/bold] [cyan]{self.model_name}[/cyan]")
                    installed = self.llm.list_installed_models()
                    console.print(f"[dim]Installed models in Ollama: {', '.join(installed)}[/dim]")
                continue

            # Autonomous delivery/recipe action or general chat
            if is_order_or_recipe_intent(user_input):
                try:
                    self.delivery_agent.execute_order(prompt=user_input)
                except KeyboardInterrupt:
                    console.print("\n[yellow]⏸️ Action interrupted by user.[/yellow]")
                except Exception as e:
                    console.print(f"\n[bold red]Execution Error:[/bold red] {e}")
            else:
                self.handle_conversational_query(user_input)
