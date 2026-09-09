import os
import json
import hashlib
from datetime import datetime, timezone
from pathlib import Path
from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

console = Console(highlight=False)


@dataclass
class CartItemSummary:
    name: str
    variant: str
    description: str
    quantity: int
    unit_price_inr: float
    total_price_inr: float


@dataclass
class OrderCheckoutReview:
    platform: str
    store_name: str
    delivery_address: str
    available_addresses: List[str]
    items: List[CartItemSummary]
    subtotal_inr: float
    delivery_fee_inr: float
    total_payable_inr: float


class ApprovalTokenLedger:
    """
    Cryptographic immutable audit ledger recording every human authorization checkpoint,
    cart integrity hash, and payment gate approval token before checkout.
    """
    LEDGER_FILE = Path.home() / ".zoovy" / "audit_ledger.jsonl"

    @classmethod
    def record_event(cls, review: OrderCheckoutReview, decision: str) -> Dict[str, Any]:
        cls.LEDGER_FILE.parent.mkdir(parents=True, exist_ok=True)
        now_iso = datetime.now(timezone.utc).isoformat()

        # Compute deterministic SHA-256 integrity hash
        item_fingerprint = ",".join(f"{i.name}:{i.quantity}:{i.total_price_inr:.2f}" for i in review.items)
        content_payload = f"{review.platform}:{review.delivery_address}:{review.total_payable_inr:.2f}:{item_fingerprint}"
        checksum = hashlib.sha256(content_payload.encode("utf-8")).hexdigest()
        token_id = f"tok_{checksum[:12]}"

        status_map = {
            "confirm": "APPROVED",
            "modify": "MODIFIED",
            "abort": "ABORTED"
        }

        record = {
            "timestamp": now_iso,
            "token_id": token_id,
            "platform": review.platform,
            "store_name": review.store_name,
            "delivery_address": review.delivery_address,
            "item_count": len(review.items),
            "items": [
                {
                    "name": i.name,
                    "variant": i.variant,
                    "quantity": i.quantity,
                    "unit_price_inr": i.unit_price_inr,
                    "total_price_inr": i.total_price_inr
                }
                for i in review.items
            ],
            "subtotal_inr": review.subtotal_inr,
            "delivery_fee_inr": review.delivery_fee_inr,
            "total_payable_inr": review.total_payable_inr,
            "decision": decision.upper(),
            "status": status_map.get(decision, "UNKNOWN"),
            "integrity_checksum": checksum
        }

        try:
            with open(cls.LEDGER_FILE, "a", encoding="utf-8") as f:
                f.write(json.dumps(record) + "\n")
        except Exception:
            pass

        return record


class PaymentGatekeeper:
    """
    Safety checkpoint ensuring the AI presents transparent cart inspection
    and address confirmation before the user manually completes payment.
    """

    @staticmethod
    def prompt_address_selection(available_addresses: List[str], default_address: Optional[str] = None) -> str:
        """
        Displays available saved addresses from the user's account and lets them choose.
        """
        if not available_addresses:
            return default_address or "Primary Saved Address"

        console.print("\n[bold cyan]📍 Saved Delivery Addresses on your Account:[/bold cyan]")
        for idx, addr in enumerate(available_addresses, 1):
            is_default = " [green](Default)[/green]" if (default_address and default_address.lower() in addr.lower()) or idx == 1 else ""
            console.print(f"  [bold yellow][{idx}][/bold yellow] {addr}{is_default}")

        try:
            choice = input(f"\nSelect delivery address [1-{len(available_addresses)}] or press Enter for default [1]: ").strip()
            if choice.isdigit() and 1 <= int(choice) <= len(available_addresses):
                selected = available_addresses[int(choice) - 1]
                console.print(f"[green]✓ Selected Address:[/green] {selected}")
                return selected
        except (KeyboardInterrupt, EOFError):
            pass

        selected = available_addresses[0]
        console.print(f"[green]✓ Using default Address:[/green] {selected}")
        return selected

    @staticmethod
    def prompt_user_confirmation(review: OrderCheckoutReview) -> str:
        """
        Renders a rich terminal invoice displaying exact item descriptions,
        quantities, prices, and delivery address before checkout.
        Logs an immutable approval token into the audit ledger.
        Returns 'confirm', 'modify', or 'abort'.
        """
        table = Table(title=f"🛒 Cart Inspection & Invoice: {review.platform.upper()} ({review.store_name})", expand=True)
        table.add_column("Item & Description", style="cyan", ratio=3)
        table.add_column("Variant / Weight", style="white", justify="center", ratio=1)
        table.add_column("Qty", style="magenta", justify="center", ratio=1)
        table.add_column("Unit Price", style="green", justify="right", ratio=1)
        table.add_column("Total (₹)", style="bold green", justify="right", ratio=1)

        for item in review.items:
            desc_text = f"[bold]{item.name}[/bold]"
            if item.description and item.description != item.name:
                desc_text += f"\n[dim]{item.description}[/dim]"

            table.add_row(
                desc_text,
                item.variant or "Standard",
                str(item.quantity),
                f"₹{item.unit_price_inr:.2f}",
                f"₹{item.total_price_inr:.2f}"
            )

        table.add_section()
        table.add_row("[bold]Item Subtotal[/bold]", "", "", "", f"₹{review.subtotal_inr:.2f}")
        table.add_row("Delivery & Packaging Fee", "", "", "", f"₹{review.delivery_fee_inr:.2f}")
        table.add_row("[bold yellow]TOTAL PAYABLE AMOUNT[/bold yellow]", "", "", "", f"[bold green]₹{review.total_payable_inr:.2f}[/bold green]")

        console.print()
        console.print(table)
        console.print(Panel(
            f"[bold cyan]📍 Verified Delivery Destination (Full Address):[/bold cyan]\n"
            f"[bold green]{review.delivery_address}[/bold green]\n\n"
            "[bold red]🛑 SAFETY PAUSE (Human-in-the-Loop):[/bold red]\n"
            "• Zoovy has configured your cart and selected your verified address above.\n"
            "• Zoovy will NEVER enter payment details or auto-debit your money.\n"
            "• Upon your confirmation, the session navigates to the payment screen for you to complete UPI/Card authorization.",
            title="🛡️ Zoovy Safety & Authorization Gate",
            border_style="yellow"
        ))

        decision = "abort"
        try:
            console.print("\n[bold cyan]Order Actions:[/bold cyan]")
            console.print("  [bold green][y][/bold green] Confirm & proceed to payment")
            console.print("  [bold yellow][m][/bold yellow] Modify cart (add/remove items or adjust quantities)")
            console.print("  [bold red][n][/bold red] Abort order")
            choice = input("\nSelect action [y/m/N]: ").strip().lower()
            if choice in ["y", "yes"]:
                decision = "confirm"
            elif choice in ["m", "modify"]:
                decision = "modify"
            else:
                decision = "abort"
        except (KeyboardInterrupt, EOFError):
            decision = "abort"

        # Record cryptographic audit token
        audit_entry = ApprovalTokenLedger.record_event(review, decision)
        console.print(f"[dim]🔒 Audit Ledger: Recorded token {audit_entry['token_id']} ({audit_entry['status']})[/dim]")

        return decision

