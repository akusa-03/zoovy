from dataclasses import dataclass
from typing import List
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

console = Console()


@dataclass
class CartItemSummary:
    name: str
    quantity: int
    unit: str
    price_inr: float


@dataclass
class OrderCheckoutReview:
    platform: str
    store_name: str
    delivery_address: str
    items: List[CartItemSummary]
    subtotal_inr: float
    delivery_fee_inr: float
    total_payable_inr: float


class PaymentGatekeeper:
    """
    Safety checkpoint to ensure the AI never executes financial transactions
    without explicit, interactive user authorization.
    """

    @staticmethod
    def prompt_user_confirmation(review: OrderCheckoutReview) -> bool:
        """
        Renders a detailed terminal invoice and halts execution for user decision.
        """
        table = Table(title=f"🛒 Checkout Invoice: {review.platform.upper()} ({review.store_name})", expand=True)
        table.add_column("Item", style="cyan", no_wrap=True)
        table.add_column("Qty", style="magenta", justify="center")
        table.add_column("Unit", style="white")
        table.add_column("Price (₹)", style="green", justify="right")

        for item in review.items:
            table.add_row(item.name, str(item.quantity), item.unit, f"₹{item.price_inr:.2f}")

        table.add_section()
        table.add_row("Subtotal", "", "", f"₹{review.subtotal_inr:.2f}")
        table.add_row("Delivery & Fees", "", "", f"₹{review.delivery_fee_inr:.2f}")
        table.add_row("[bold yellow]TOTAL PAYABLE[/bold yellow]", "", "", f"[bold green]₹{review.total_payable_inr:.2f}[/bold green]")

        console.print()
        console.print(table)
        console.print(Panel(
            f"[bold]Delivery Address:[/bold] {review.delivery_address}
"
            f"[bold red]SAFETY PAUSE:[/bold red] The AI will STOP here. "
            "Please verify the cart and complete payment manually in the browser window.",
            title="🛡️ Zoovy Safety Firewall",
            border_style="yellow"
        ))

        try:
            choice = input("
Complete payment manually in the opened browser? [y/N]: ").strip().lower()
            return choice in ["y", "yes"]
        except KeyboardInterrupt:
            return False
