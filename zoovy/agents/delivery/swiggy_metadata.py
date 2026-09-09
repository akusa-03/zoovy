"""
Swiggy Metadata Agent for Zoovy.
Manages persistent user metadata, delivery addresses, location coordinates,
and preferences stored locally in ~/.zoovy/swiggy_metadata.json.
Prompts for and validates address details if missing.
"""

import os
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

    def resolve_or_prompt_address(self, preferred_tag: Optional[str] = None) -> Dict[str, Any]:
        """
        Returns an address matching preferred_tag or default.
        If no addresses exist, prompts the user and saves it.
        """
        if not self.has_addresses():
            return self.ask_and_store_address(tag=preferred_tag)

        # Check existing
        addr = self.get_address(preferred_tag)
        if addr:
            console.print(f"[cyan]📍 [Swiggy Metadata][/cyan] Using delivery address: [bold]{addr['tag']} - {addr.get('formatted')}[/bold]")
            return addr

        # If tag specified was not found, prompt to select or create
        addrs = self.get_addresses()
        console.print(f"\n[yellow]Address label '{preferred_tag}' not found among saved addresses:[/yellow]")
        for idx, (t, a) in enumerate(addrs.items(), 1):
            console.print(f"  [{idx}] {t}: {a.get('formatted')}")
        console.print(f"  [{len(addrs) + 1}] Add new address")

        try:
            choice = input(f"Select address [1-{len(addrs) + 1}, default: 1]: ").strip() or "1"
            c_int = int(choice)
            if 1 <= c_int <= len(addrs):
                chosen_tag = list(addrs.keys())[c_int - 1]
                return addrs[chosen_tag]
            else:
                return self.ask_and_store_address()
        except (ValueError, KeyboardInterrupt, EOFError):
            return next(iter(addrs.values()))

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
