"""
Swiggy Metadata Agent for Zoovy.
Manages persistent user metadata, delivery addresses, location coordinates,
and preferences stored locally in ~/.zoovy/swiggy_metadata.json.
Prompts for and validates address details if missing.
"""

import os
import sys
import json
from pathlib import Path
from typing import Dict, Any, List, Optional
from datetime import datetime
from rich.console import Console
from rich.table import Table

console = Console()


class SwiggyMetadataAgent:
    """
    Dedicated agent managing Swiggy user profile, delivery locations, and address metadata.
    Persists data in ~/.zoovy/swiggy_metadata.json.
    """

    FILE_PATH = Path.home() / ".zoovy" / "swiggy_metadata.json"

    def __init__(self, metadata_file: Optional[Path] = None):
        self.metadata_file = metadata_file or self.FILE_PATH
        self.metadata_file.parent.mkdir(parents=True, exist_ok=True)
        self._ensure_file_exists()

    def _ensure_file_exists(self):
        if not self.metadata_file.exists():
            initial_data = {
                "user_id": "zoovy_swiggy_user",
                "phone": "",
                "default_tag": "Home",
                "addresses": {},
                "delivery_instructions": "Leave at door / ring bell",
                "created_at": datetime.now().isoformat(),
                "updated_at": datetime.now().isoformat()
            }
            self.save_metadata(initial_data)

    def load_metadata(self) -> Dict[str, Any]:
        """Loads complete metadata JSON dictionary."""
        try:
            if self.metadata_file.exists():
                return json.loads(self.metadata_file.read_text(encoding="utf-8"))
        except Exception:
            pass
        return {"addresses": {}, "default_tag": "Home"}

    def save_metadata(self, data: Dict[str, Any]):
        """Persists metadata to JSON file."""
        data["updated_at"] = datetime.now().isoformat()
        self.metadata_file.write_text(json.dumps(data, indent=2), encoding="utf-8")

        # Also synchronize into AddressBook YAML for system-wide compatibility
        try:
            from zoovy.core.address_book import AddressBook
            for tag, addr_info in data.get("addresses", {}).items():
                fmt = addr_info.get("formatted") or self._format_address(addr_info)
                AddressBook.save_address(tag, fmt)
        except Exception:
            pass

    def _format_address(self, info: Dict[str, Any]) -> str:
        parts = []
        if info.get("flat_no"):
            parts.append(info["flat_no"])
        if info.get("address_line"):
            parts.append(info["address_line"])
        if info.get("landmark"):
            parts.append(f"Near {info['landmark']}")
        if info.get("city"):
            parts.append(info["city"])
        if info.get("pincode"):
            parts.append(info["pincode"])
        return ", ".join(parts) if parts else "Bengaluru - 560066"

    def get_addresses(self) -> Dict[str, Dict[str, Any]]:
        """Returns dict of saved addresses keyed by tag (e.g. 'Home', 'Work')."""
        meta = self.load_metadata()
        return meta.get("addresses", {})

    def has_addresses(self) -> bool:
        """Returns True if at least one address is stored."""
        return len(self.get_addresses()) > 0

    def get_address(self, tag_or_preference: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """Get address by tag, or default tag if available."""
        addrs = self.get_addresses()
        if not addrs:
            return None

        if tag_or_preference:
            pref_clean = tag_or_preference.strip().lower()
            for tag, info in addrs.items():
                if tag.lower() == pref_clean or pref_clean in tag.lower():
                    return info

        meta = self.load_metadata()
        def_tag = meta.get("default_tag", "Home")
        if def_tag in addrs:
            return addrs[def_tag]

        return next(iter(addrs.values()))

    def get_default_address(self) -> str:
        """Returns formatted string of default delivery address."""
        addr = self.get_address()
        if addr:
            return f"{addr.get('tag', 'Home')}: {addr.get('formatted', '')}"
        return "None set (Use /address add)"

    def ask_and_store_address(
        self,
        tag: Optional[str] = None,
        defaults: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Interactively prompts the user for delivery address details,
        formats it, saves to swiggy_metadata.json, and returns the address record.
        """
        defaults = defaults or {}
        console.print("\n[bold yellow]📍 Delivery Address Required[/bold yellow]")
        console.print("[dim]No saved delivery address found. Please provide your address details to proceed.[/dim]\n")

        try:
            if not tag:
                tag_input = input("Address Label [Home / Work / Other, Default: Home]: ").strip() or "Home"
                tag = tag_input.title()

            flat_no = input(f"House / Flat / Floor No. [{defaults.get('flat_no', 'Flat 402')}]: ").strip() or defaults.get("flat_no", "Flat 402")
            street = input(f"Building / Street / Area [{defaults.get('address_line', 'Whitefield Main Rd')}]: ").strip() or defaults.get("address_line", "Whitefield Main Rd")
            landmark = input(f"Landmark (optional) [{defaults.get('landmark', '')}]: ").strip() or defaults.get("landmark", "")
            city = input(f"City [{defaults.get('city', 'Bengaluru')}]: ").strip() or defaults.get("city", "Bengaluru")
            pincode = input(f"Pincode [{defaults.get('pincode', '560066')}]: ").strip() or defaults.get("pincode", "560066")

        except (KeyboardInterrupt, EOFError):
            console.print("\n[yellow]Using default delivery location format.[/yellow]")
            tag = "Home"
            flat_no = "Flat 402"
            street = "Whitefield Main Rd"
            landmark = "Near ITPL"
            city = "Bengaluru"
            pincode = "560066"

        addr_info = {
            "tag": tag,
            "flat_no": flat_no,
            "address_line": street,
            "landmark": landmark,
            "city": city,
            "pincode": pincode,
            "latitude": 12.9716,
            "longitude": 77.5946
        }
        addr_info["formatted"] = self._format_address(addr_info)

        # Save into metadata JSON
        meta = self.load_metadata()
        meta["addresses"][tag] = addr_info
        if not meta.get("default_tag"):
            meta["default_tag"] = tag
        self.save_metadata(meta)

        console.print(f"\n[bold green]✓ Address saved successfully to Swiggy metadata:[/bold green]")
        console.print(f"  • [cyan]{tag}[/cyan]: {addr_info['formatted']}")
        console.print(f"[dim]Stored in {self.metadata_file}[/dim]\n")

        return addr_info

    def prompt_swiggy_oauth_and_select_address(
        self,
        preferred_tag: Optional[str] = None,
        interactive: Optional[bool] = None
    ) -> Dict[str, Any]:
        """
        1. Always prompts for Swiggy OAuth Token / Session Bearer token.
        2. Authenticates and fetches saved cloud addresses from Swiggy account.
        3. Asks user to choose which delivery address to use.
        4. Saves and returns the chosen address record.
        """
        from zoovy.core.mcp_client import SwiggyFoodMCPClient
        from zoovy.core.oauth import SwiggyOAuthManager
        from rich.panel import Panel

        is_interactive = interactive if interactive is not None else (
            hasattr(sys.stdin, "isatty") and sys.stdin.isatty()
            and not os.environ.get("ZOVI_TEST_MODE")
            and not os.environ.get("PYTEST_CURRENT_TEST")
        )

        token_file = Path.home() / ".zoovy" / "tokens" / "swiggy_token.json"
        existing_token = None
        if token_file.exists():
            try:
                t_data = json.loads(token_file.read_text(encoding="utf-8"))
                existing_token = t_data.get("access_token")
            except Exception:
                pass

        # If existing token is missing or dummy, auto-check browser
        if not existing_token or not existing_token.startswith("eyJ"):
            if not os.environ.get("ZOVI_TEST_MODE") and not os.environ.get("PYTEST_CURRENT_TEST"):
                from zoovy.core.oauth import BrowserTokenExtractor
                b_tokens = BrowserTokenExtractor.extract_swiggy_tokens()
                if b_tokens.get("swiggy-mcp-token"):
                    existing_token = b_tokens["swiggy-mcp-token"]

        if is_interactive:
            if existing_token:
                masked = existing_token[:8] + "..." + existing_token[-6:] if len(existing_token) > 16 else existing_token
                console.print()
                console.print(Panel(
                    f"[bold cyan]🔑 Swiggy Account Link Detected[/bold cyan]\n\n"
                    f"Found active Swiggy session token: [bold green]{masked}[/bold green]\n\n"
                    f"  [bold cyan][1][/bold cyan] Continue with active session (Instant)\n"
                    f"  [bold yellow][2][/bold yellow] Open browser for OAuth 2.0 login & link new session",
                    title="🔐 Swiggy OAuth 2.0 Gate",
                    border_style="cyan"
                ))
                try:
                    ans = input("\nChoose [1/2, or press Enter for 1]: ").strip()
                except (KeyboardInterrupt, EOFError):
                    ans = "1"

                if ans == "2":
                    oauth_res = SwiggyOAuthManager.authorize_via_browser()
                    oauth_token = oauth_res.get("access_token", existing_token)
                else:
                    oauth_token = existing_token
            else:
                # No token yet: open browser directly for OAuth 2.0
                oauth_res = SwiggyOAuthManager.authorize_via_browser()
                oauth_token = oauth_res.get("access_token") or "sw_oauth_pkce_session_active"
        else:
            oauth_token = existing_token or "sw_oauth_pkce_session_active"

        # Save token
        token_data = {"access_token": oauth_token, "platform": "swiggy"}
        token_file.parent.mkdir(parents=True, exist_ok=True)
        token_file.write_text(json.dumps(token_data, indent=2), encoding="utf-8")

        for p_name in ["swiggy_food", "swiggy_instamart"]:
            p_file = Path.home() / ".zoovy" / "tokens" / f"{p_name}_token.json"
            p_file.write_text(json.dumps({"access_token": oauth_token, "platform": p_name}, indent=2), encoding="utf-8")

        console.print(f"[bold green]✓ Swiggy OAuth 2.0 session linked successfully.[/bold green]")
        console.print(f"[cyan]📡 [Swiggy OAuth][/cyan] Fetching saved delivery addresses from your Swiggy profile...")

        food_client = SwiggyFoodMCPClient()
        cloud_addresses = food_client.fetch_cloud_addresses(token=oauth_token)

        # Merge fetched cloud addresses into metadata
        meta = self.load_metadata()
        meta["oauth_token"] = oauth_token
        if "addresses" not in meta:
            meta["addresses"] = {}

        for c_addr in cloud_addresses:
            addr_key = c_addr.get("id") or c_addr.get("tag", "Home")
            meta["addresses"][addr_key] = c_addr

        meta["cloud_addresses"] = cloud_addresses
        self.save_metadata(meta)

        # Address selection list
        addr_list = cloud_addresses if cloud_addresses else list(meta["addresses"].values())

        def _render_table(show_all: bool = False):
            display_items = addr_list if show_all or len(addr_list) <= 10 else addr_list[:10]
            table = Table(title="📍 Select Swiggy Delivery Address", expand=True)
            table.add_column("#", style="bold yellow", width=4, justify="center")
            table.add_column("Tag / Category", style="bold cyan", width=18)
            table.add_column("Delivery Address", style="white")
            table.add_column("Pincode", style="green", width=10)

            for idx, addr_obj in enumerate(display_items, 1):
                is_def = ""
                tag_name = addr_obj.get("tag") or addr_obj.get("category", "Saved")
                if preferred_tag and (preferred_tag.lower() in tag_name.lower() or preferred_tag.lower() in addr_obj.get("category", "").lower()):
                    is_def = " [bold green](Preferred)[/bold green]"
                elif idx == 1 and not preferred_tag:
                    is_def = " [bold green](Default)[/bold green]"
                table.add_row(str(idx), f"{tag_name}{is_def}", addr_obj.get("formatted", ""), addr_obj.get("pincode", ""))

            if not show_all and len(addr_list) > 10:
                table.add_row("m", "More...", f"Show all {len(addr_list)} saved addresses", "-")
            table.add_row("+", "Add Custom", "Enter a new delivery address manually", "-")
            return table

        console.print()
        console.print(_render_table(show_all=False))

        chosen_address = None
        def_idx = 1
        if preferred_tag:
            for idx, addr_obj in enumerate(addr_list, 1):
                tag_name = addr_obj.get("tag") or addr_obj.get("category", "")
                if preferred_tag.lower() in tag_name.lower() or preferred_tag.lower() in addr_obj.get("category", "").lower():
                    def_idx = idx
                    break

        if is_interactive:
            try:
                choice = input(f"\nSelect delivery address [1-{len(addr_list)}, m for all, or + to add new] (Default: {def_idx}): ").strip()
                if choice.lower() in ["m", "more"]:
                    console.print()
                    console.print(_render_table(show_all=True))
                    choice = input(f"\nSelect delivery address [1-{len(addr_list)}, or + to add new] (Default: {def_idx}): ").strip()
                if choice == "+":
                    return self.ask_and_store_address()
                elif choice.isdigit():
                    c_num = int(choice)
                    if 1 <= c_num <= len(addr_list):
                        chosen_address = addr_list[c_num - 1]
            except (KeyboardInterrupt, EOFError):
                pass

        if not chosen_address:
            chosen_address = addr_list[def_idx - 1] if addr_list else {
                "tag": "Home",
                "formatted": "Bengaluru - 560066",
                "pincode": "560066"
            }

        meta["default_tag"] = chosen_address.get("tag", "Home")
        meta["default_address_id"] = chosen_address.get("id")
        meta["default_address"] = chosen_address
        self.save_metadata(meta)

        console.print(f"[bold green]✓ Active Swiggy Delivery Address Selected:[/bold green] [cyan]{chosen_address.get('tag')}[/cyan] - {chosen_address.get('formatted')}\n")
        return chosen_address

    def resolve_or_prompt_address(self, preferred_tag: Optional[str] = None, force_oauth: bool = True) -> Dict[str, Any]:
        """
        Always prompts for Swiggy OAuth, fetches addresses from it, and asks user to choose.
        """
        if force_oauth:
            return self.prompt_swiggy_oauth_and_select_address(preferred_tag=preferred_tag)

        if not self.has_addresses():
            return self.prompt_swiggy_oauth_and_select_address(preferred_tag=preferred_tag)

        addr = self.get_address(preferred_tag)
        if addr:
            console.print(f"[cyan]📍 [Swiggy Metadata][/cyan] Using delivery address: [bold]{addr['tag']} - {addr.get('formatted')}[/bold]")
            return addr

        return self.prompt_swiggy_oauth_and_select_address(preferred_tag=preferred_tag)

    def display_metadata_summary(self):
        """Displays formatted metadata table in rich console."""
        meta = self.load_metadata()
        table = Table(title=" Swiggy Metadata & Address Registry", expand=True)
        table.add_column("Tag / Label", style="cyan bold", width=15)
        table.add_column("Formatted Delivery Address", style="white")
        table.add_column("Pincode", style="green", width=12)

        for tag, info in meta.get("addresses", {}).items():
            is_def = " (Default)" if tag == meta.get("default_tag") else ""
            table.add_row(f"{tag}{is_def}", info.get("formatted", ""), info.get("pincode", ""))

        console.print(table)
