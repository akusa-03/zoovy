import sys
import time
from rich.console import Console
from ...core.llm import OllamaClient
from ...core.safety import PaymentGatekeeper, OrderCheckoutReview
from .schemas import OrderIntent, DeliveryPlatform
from .browser import BrowserSessionManager
from .platforms.zepto import ZeptoDriver
from .platforms.swiggy import SwiggyDriver
from .platforms.zomato import ZomatoDriver

console = Console()


class DeliveryAgent:
    """
    Autonomous agent orchestrating natural language requests into browser operations
    for Zepto, Swiggy, and Zomato.
    """

    SYSTEM_PROMPT = """You are Zoovy's Delivery Intelligence Agent.
Your task is to parse the user's natural language request into a strict JSON OrderIntent.
Supported platforms: 'zepto' (groceries/quick-commerce), 'swiggy' (food/groceries), 'zomato' (food).

Output JSON schema:
{
  "platform": "zepto" | "swiggy" | "zomato",
  "items": [
    {
      "query": "search keyword",
      "quantity": integer,
      "preferred_variant": "brand or weight variant e.g. 500g"
    }
  ],
  "address_preference": "Home"
}
"""

    def __init__(self, llm_client: OllamaClient):
        self.llm = llm_client

    def parse_request(self, user_prompt: str, default_platform: Optional[str] = None) -> OrderIntent:
        messages = [
            {"role": "system", "content": self.SYSTEM_PROMPT},
            {"role": "user", "content": f"Request: {user_prompt}\nDefault platform hint: {default_platform or 'auto'}"}
        ]
        parsed_json = self.llm.chat_structured(messages, schema={})
        return OrderIntent(**parsed_json)

    def execute_order(self, prompt: str, platform_override: Optional[str] = None):
        console.print(f"[bold cyan]🧠 Interpreting request:[/bold cyan] '{prompt}'")
        intent = self.parse_request(prompt, platform_override)

        console.print(f"[green]✓ Target Platform:[/green] [bold]{intent.platform.value.upper()}[/bold]")
        console.print(f"[green]✓ Items to order:[/green] {len(intent.items)}")
        for it in intent.items:
            console.print(f"   • {it.quantity}x {it.query} ({it.preferred_variant or 'standard'})")

        # Launch Browser Session
        session = BrowserSessionManager(platform_name=intent.platform.value, headless=False)
        try:
            console.print("
[bold yellow]🌐 Launching browser with persistent session...[/bold yellow]")
            page = session.start()

            if intent.platform == DeliveryPlatform.ZEPTO:
                driver = ZeptoDriver(page)
            elif intent.platform == DeliveryPlatform.SWIGGY:
                driver = SwiggyDriver(page)
            else:
                driver = ZomatoDriver(page)

            console.print(f"Navigating to {intent.platform.value}...")
            driver.navigate_home()

            # Search & Add Items
            for item in intent.items:
                console.print(f"
[cyan]🔍 Searching for:[/cyan] '{item.query}'...")
                results = driver.search_product(item.query)
                console.print(f"Adding {item.quantity}x '{item.query}' to cart...")
                driver.add_to_cart(product_index=0, quantity=item.quantity)

            # View Cart & Navigate to Checkout
            console.print("
[bold yellow]🛒 Finalizing cart and navigating to checkout...[/bold yellow]")
            driver.navigate_to_checkout()
            cart_items = driver.inspect_cart()

            # Safety Breakpoint: Prompt User
            subtotal = sum(i.price_inr * i.quantity for i in cart_items)
            review = OrderCheckoutReview(
                platform=intent.platform.value,
                store_name=f"{intent.platform.value.capitalize()} Store",
                delivery_address=intent.address_preference or "Saved Default Address",
                items=cart_items,
                subtotal_inr=subtotal,
                delivery_fee_inr=25.0,
                total_payable_inr=subtotal + 25.0
            )

            confirmed = PaymentGatekeeper.prompt_user_confirmation(review)
            if confirmed:
                console.print("[bold green]✓ User authorized. Browser remains open for final payment.[/bold green]")
                input("Press [Enter] after you have completed payment to finish the session...")
            else:
                console.print("[bold red]✗ Order aborted by user. No payment executed.[/bold red]")

        finally:
            session.close()
            console.print("[dim]Browser session closed.[/dim]")
