from dataclasses import dataclass, field
from typing import List, Optional
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

        try:
            console.print("\n[bold cyan]Order Actions:[/bold cyan]")
            console.print("  [bold green][y][/bold green] Confirm & proceed to payment")
            console.print("  [bold yellow][m][/bold yellow] Modify cart in browser (add/remove items or adjust quantities)")
            console.print("  [bold red][n][/bold red] Abort order")
            choice = input("\nSelect action [y/m/N]: ").strip().lower()
            if choice in ["y", "yes"]:
                return "confirm"
            elif choice in ["m", "modify"]:
                return "modify"
            return "abort"
        except (KeyboardInterrupt, EOFError):
            return "abort"
