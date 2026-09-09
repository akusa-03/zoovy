import os
from pathlib import Path
from typing import Dict, List, Optional
import yaml
from rich.console import Console

console = Console()


class AddressBook:
    """
    Manages the user's real delivery addresses locally in ~/.zoovy/addresses.yaml.
    Prevents synthetic or placeholder addresses from ever being displayed.
    """
    FILE_PATH = Path.home() / ".zoovy" / "addresses.yaml"

    @classmethod
    def load_addresses(cls) -> Dict[str, str]:
        if cls.FILE_PATH.exists():
            try:
                with open(cls.FILE_PATH, "r", encoding="utf-8") as f:
                    data = yaml.safe_load(f)
                    if isinstance(data, dict):
                        return {str(k): str(v) for k, v in data.items()}
            except Exception:
                pass
        return {}

    @classmethod
    def save_address(cls, label: str, full_address: str):
        cls.FILE_PATH.parent.mkdir(parents=True, exist_ok=True)
        addresses = cls.load_addresses()
        clean_label = label.strip() or "Home"
        addresses[clean_label] = full_address.strip()
        with open(cls.FILE_PATH, "w", encoding="utf-8") as f:
            yaml.safe_dump(addresses, f, default_flow_style=False, sort_keys=False)

    @classmethod
    def remove_address(cls, label: str) -> bool:
        addresses = cls.load_addresses()
        clean_label = label.strip()
        if clean_label in addresses:
            del addresses[clean_label]
            with open(cls.FILE_PATH, "w", encoding="utf-8") as f:
                yaml.safe_dump(addresses, f, default_flow_style=False, sort_keys=False)
            return True
        return False

    @classmethod
    def sync_external_addresses(cls, external_addresses: List[str]):
        """
        Syncs a list of addresses (e.g. from cloud MCP or browser session)
        into the local addresses.yaml file.
        """
        for item in external_addresses:
            if " - " in item:
                lbl, addr = item.split(" - ", 1)
            elif ":" in item:
                lbl, addr = item.split(":", 1)
            else:
                lbl, addr = "Home", item
            cls.save_address(lbl.strip(), addr.strip())

    @classmethod
    def get_formatted_list(cls) -> List[str]:
        addresses = cls.load_addresses()
        return [f"{label} - {addr}" for label, addr in addresses.items()]

    @classmethod
    def get_or_prompt_addresses(cls) -> List[str]:
        """
        Returns saved addresses, or interactively asks the user to input their real address
        and saves it locally so they never have to type it again.
        """
        addresses = cls.load_addresses()
        if addresses:
            return cls.get_formatted_list()

        console.print("\n[bold yellow]📍 Delivery Address Setup Required:[/bold yellow]")
        console.print("No saved delivery address was found in your local Zoovy configuration.")
        console.print("[dim]Enter your real delivery address once. It will be saved securely in ~/.zoovy/addresses.yaml[/dim]\n")
        try:
            addr_input = input("Enter your full delivery address (e.g. Flat 302, Palm Grove, Powai, Mumbai - 400076): ").strip()
            if addr_input:
                cls.save_address("Home", addr_input)
                console.print(f"[bold green]✓ Saved as 'Home' in {cls.FILE_PATH}[/bold green]\n")
                return [f"Home - {addr_input}"]
        except (KeyboardInterrupt, EOFError):
            pass

        return ["Home - Custom Delivery Address"]
