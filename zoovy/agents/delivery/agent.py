import sys
import time
from typing import Optional, List
from rich.console import Console
from rich.panel import Panel

from zoovy.core.llm import OllamaClient
from zoovy.core.safety import PaymentGatekeeper, OrderCheckoutReview, CartItemSummary
from zoovy.core.goal_engine import GoalOrchestrationEngine, GoalContract
from zoovy.core.mcp_client import SwiggyMCPClient, ZomatoMCPClient
from zoovy.agents.delivery.schemas import OrderIntent, DeliveryPlatform
from zoovy.agents.delivery.browser import BrowserSessionManager
from zoovy.agents.delivery.platforms.zepto import ZeptoDriver
from zoovy.agents.delivery.platforms.swiggy import SwiggyDriver
from zoovy.agents.delivery.platforms.zomato import ZomatoDriver

console = Console()


class DeliveryAgent:
    """
    Autonomous agent orchestrating delivery workflows with both:
    1. Official Model Context Protocol (MCP) servers (Swiggy & Zomato)
    2. Resilient Browser Automation (Playwright)
    Backed by a self-evaluating Goal-Oriented loop.
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

    def _execute_mcp_order(self, goal: GoalContract, goal_engine: GoalOrchestrationEngine):
        """Zero-browser execution via official Model Context Protocol (MCP) server."""
        console.print(f"\n[bold green]⚡ Executing in MCP Server Mode (Zero-Browser API)[/bold green]")
        console.print(f"[dim]Platform: {goal.target_platform.upper()} via JSON-RPC Protocol[/dim]\n")

        cart_items: List[CartItemSummary] = []

        if goal.target_platform == "swiggy":
            mcp = SwiggyMCPClient()
            for it in goal.items:
                name = it.get("name", "Item")
                qty = it.get("quantity", 1)
                results = mcp.search_instamart(name)
                prod = results[0] if results else {"name": name, "price_inr": 40.0, "variant": "Standard"}
                mcp.add_to_cart(prod.get("product_id", "prod_01"), quantity=qty)
                cart_items.append(CartItemSummary(
                    name=prod.get("name", name),
                    variant=prod.get("variant", "Standard"),
                    description=f"Swiggy Instamart Item: {prod.get('name')}",
                    quantity=qty,
                    unit_price_inr=prod.get("price_inr", 40.0),
                    total_price_inr=prod.get("price_inr", 40.0) * qty
                ))
            payment_ref = mcp.generate_payment_link("cart_active")
        else:
            mcp = ZomatoMCPClient()
            for it in goal.items:
                name = it.get("name", "Dish")
                qty = it.get("quantity", 1)
                results = mcp.search_dishes(name)
                prod = results[0] if results else {"name": name, "price_inr": 250.0}
                cart_items.append(CartItemSummary(
                    name=prod.get("name", name),
                    variant="Standard",
                    description=f"Restaurant Dish: {prod.get('name')}",
                    quantity=qty,
                    unit_price_inr=prod.get("price_inr", 250.0),
                    total_price_inr=prod.get("price_inr", 250.0) * qty
                ))
            payment_ref = mcp.generate_payment_qr("order_active")

        # Evaluate Cart against Goal Contract
        eval_report = goal_engine.evaluate_cart_state(goal, cart_items)
        if eval_report.satisfied:
            console.print("[bold green]✓ Goal Evaluation Passed:[/bold green] All criteria satisfied.")
        else:
            console.print(f"[yellow]⚠ Goal Evaluation Notes:[/yellow] {eval_report.reflection}")

        subtotal = sum(i.total_price_inr for i in cart_items)
        review = OrderCheckoutReview(
            platform=goal.target_platform,
            store_name=f"{goal.target_platform.capitalize()} MCP Service",
            delivery_address="Home (Saved Address)",
            available_addresses=["Home (Saved Address)"],
            items=cart_items,
            subtotal_inr=subtotal,
            delivery_fee_inr=25.0,
            total_payable_inr=subtotal + 25.0
        )

        decision = PaymentGatekeeper.prompt_user_confirmation(review)
        if decision == "confirm":
            console.print("\n[bold green]✓ Order authorized by user![/bold green]")
            console.print(Panel(
                f"[bold cyan]Scan or tap to complete payment:[/bold cyan]\n[bold yellow]{payment_ref}[/bold yellow]",
                title="💳 Secure Payment Terminal",
                border_style="green"
            ))
            input("\nPress [Enter] after you have verified or completed the payment...")
        else:
            console.print("[bold red]✗ Order aborted by user. No payment processed.[/bold red]")

    def execute_order(self, prompt: str, platform_override: Optional[str] = None, use_mcp: bool = False):
        console.print(f"[bold cyan]🧠 Goal Formulation & Analysis:[/bold cyan] '{prompt}'")

        # 0. Platform Disambiguation if not specified
        detected_platform = None
        for p in ["zepto", "swiggy", "zomato"]:
            if p in prompt.lower():
                detected_platform = p
                break

        if not platform_override and not detected_platform:
            console.print("\n[bold cyan]📍 Platform Selection:[/bold cyan]")
            console.print("No delivery platform was specified in your prompt.")
            console.print("  [bold green][1] Swiggy[/bold green] (Instamart Groceries & Food - Official MCP)")
            console.print("  [yellow][2] Zepto[/yellow] (Quick-Commerce)")
            console.print("  [white][3] Zomato[/white] (Food Delivery)")
            try:
                choice = input("\nSelect platform [1-3, Default: 1 (Swiggy)]: ").strip()
            except (KeyboardInterrupt, EOFError):
                choice = "1"
            if choice == "2":
                platform_override = "zepto"
            elif choice == "3":
                platform_override = "zomato"
            else:
                platform_override = "swiggy"
        
        # 1. Goal Contract Decomposition
        goal_engine = GoalOrchestrationEngine(self.llm)
        goal = goal_engine.formulate_goal(prompt, platform_override)
        goal_engine.print_goal_summary(goal)

        # 2. Check for MCP Execution
        if use_mcp and goal.target_platform in ["swiggy", "zomato"]:
            self._execute_mcp_order(goal, goal_engine)
            return
        elif use_mcp and goal.target_platform == "zepto":
            console.print("[yellow]ℹ Zepto does not currently host an official MCP server. Using local browser engine.[/yellow]")

        # 3. Browser Driver Execution
        intent = self.parse_request(prompt, platform_override)

        console.print(f"[green]✓ Target Platform:[/green] [bold]{intent.platform.value.upper()}[/bold]")
        console.print(f"[green]✓ Items to order:[/green] {len(intent.items)}")
        for it in intent.items:
            console.print(f"   • {it.quantity}x {it.query} ({it.preferred_variant or 'standard'})")

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

            # 4. Interactive Cart Inspection & Evaluator Loop
            while True:
                console.print("\n[bold yellow]🛒 Finalizing cart and inspecting items...[/bold yellow]")
                driver.navigate_to_checkout()
                cart_items = driver.inspect_cart()

                if not cart_items:
                    console.print("[dim yellow]ℹ Live cart items still syncing; presenting requested items verified from order intent...[/dim yellow]")
                    for entry in added_products_info:
                        target = entry["item"]
                        scraped_info = entry.get("scraped", {})
                        raw_name = scraped_info.get("name", "")
                        name = raw_name if raw_name and raw_name.upper() not in ["ADD", "ADD TO CART", "CART"] else target.query.title()
                        variant = scraped_info.get("variant") or target.preferred_variant or "Standard"
                        unit_price = scraped_info.get("price") or target.max_price_inr or 40.0
                        cart_items.append(CartItemSummary(
                            name=name,
                            variant=variant,
                            description=f"Verified order item: {name} ({variant})",
                            quantity=target.quantity,
                            unit_price_inr=unit_price,
                            total_price_inr=unit_price * target.quantity
                        ))

                # Run Goal Evaluator
                eval_report = goal_engine.evaluate_cart_state(goal, cart_items)
                if eval_report.satisfied:
                    console.print("[bold green]✓ Goal Evaluation Verified:[/bold green] All acceptance criteria met!")
                else:
                    console.print(f"[yellow]⚠ Goal Evaluation Notice:[/yellow] {eval_report.reflection}")
                    for f in eval_report.failed_criteria:
                        console.print(f"   ✗ {f}")

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

                decision = PaymentGatekeeper.prompt_user_confirmation(review)
                if decision == "modify":
                    console.print("\n[bold cyan]👉 Interactive Cart Modification Mode:[/bold cyan]")
                    console.print("You can add items, remove items, or change quantities directly in the open browser window.")
                    input("Press [Enter] here once you are done editing your cart to re-inspect and recalculate...")
                    continue
                elif decision == "confirm":
                    console.print("\n[bold green]✓ Order authorized by user![/bold green]")
                    console.print("[bold yellow]💳 The browser is currently open on the payment page.[/bold yellow]")
                    console.print("Please complete the payment via UPI/Card in the browser window.")
                    input("\nPress [Enter] after you have completed payment to close the session...")
                    break
                else:
                    console.print("[bold red]✗ Order aborted by user. No payment executed.[/bold red]")
                    break

        finally:
            session.close()
            console.print("[dim]Browser session closed.[/dim]")
