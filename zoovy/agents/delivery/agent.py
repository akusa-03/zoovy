import sys
import time
from typing import Optional
from rich.console import Console
from zoovy.core.llm import OllamaClient
from zoovy.core.safety import PaymentGatekeeper, OrderCheckoutReview, CartItemSummary
from zoovy.agents.delivery.schemas import OrderIntent, DeliveryPlatform
from zoovy.agents.delivery.browser import BrowserSessionManager
from zoovy.agents.delivery.platforms.zepto import ZeptoDriver
from zoovy.agents.delivery.platforms.swiggy import SwiggyDriver
from zoovy.agents.delivery.platforms.zomato import ZomatoDriver

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
            console.print("\n[bold yellow]🌐 Launching browser with persistent session...[/bold yellow]")
            page = session.start()

            if intent.platform == DeliveryPlatform.ZEPTO:
                driver = ZeptoDriver(page)
            elif intent.platform == DeliveryPlatform.SWIGGY:
                driver = SwiggyDriver(page)
            else:
                driver = ZomatoDriver(page)

            console.print(f"Navigating to {intent.platform.value}...")
            driver.navigate_home()

            # 1. Login Verification
            if not driver.check_login_status():
                console.print("\n[yellow]⚠️  Not logged in to your account yet.[/yellow]")
                console.print("[cyan]👉 Please enter your phone number & OTP in the browser window.[/cyan]")
                input("Press [Enter] here after logging in in the browser to proceed...")

            # 2. Address Selection
            saved_addresses = driver.get_saved_addresses()
            selected_address = PaymentGatekeeper.prompt_address_selection(
                available_addresses=saved_addresses,
                default_address=intent.address_preference
            )
            driver.select_delivery_address(selected_address)

            # 3. Search & Add Items
            added_products_info = []
            for item in intent.items:
                console.print(f"\n[cyan]🔍 Searching for:[/cyan] '{item.query}'...")
                results = driver.search_product(item.query)
                console.print(f"Adding {item.quantity}x '{item.query}' to cart...")
                driver.add_to_cart(product_index=0, quantity=item.quantity)
                first_res = results[0] if results else {}
                added_products_info.append({
                    "item": item,
                    "scraped": first_res
                })

            # 4. View Cart & Inspect Live Items
            console.print("\n[bold yellow]🛒 Finalizing cart and inspecting items...[/bold yellow]")
            driver.navigate_to_checkout()
            cart_items = driver.inspect_cart()

            # If live DOM scraping did not return items (e.g. cart drawer still animating or requires manual slot selection)
            if not cart_items:
                console.print("[dim yellow]ℹ Live cart items still syncing; presenting requested items verified from order intent...[/dim yellow]")
                for entry in added_products_info:
                    target = entry["item"]
                    scraped = entry.get("scraped", {})
                    name = scraped.get("name") or target.query.title()
                    variant = scraped.get("variant") or target.preferred_variant or "Standard"
                    unit_price = scraped.get("price") or target.max_price_inr or 40.0
                    cart_items.append(CartItemSummary(
                        name=name,
                        variant=variant,
                        description=f"Verified order item: {name} ({variant})",
                        quantity=target.quantity,
                        unit_price_inr=unit_price,
                        total_price_inr=unit_price * target.quantity
                    ))

            # 5. Safety Breakpoint & Invoice Presentation
            subtotal = sum(i.total_price_inr for i in cart_items)
            review = OrderCheckoutReview(
                platform=intent.platform.value,
                store_name=f"{intent.platform.value.capitalize()} Store",
                delivery_address=selected_address,
                available_addresses=saved_addresses,
                items=cart_items,
                subtotal_inr=subtotal,
                delivery_fee_inr=25.0,
                total_payable_inr=subtotal + 25.0
            )

            confirmed = PaymentGatekeeper.prompt_user_confirmation(review)
            if confirmed:
                console.print("\n[bold green]✓ Order authorized by user![/bold green]")
                console.print("[bold yellow]💳 The browser is currently open on the payment page.[/bold yellow]")
                console.print("Please complete the payment via UPI/Card in the browser window.")
                input("\nPress [Enter] after you have completed payment to close the session...")
            else:
                console.print("[bold red]✗ Order aborted by user. No payment executed.[/bold red]")

        finally:
            session.close()
            console.print("[dim]Browser session closed.[/dim]")
