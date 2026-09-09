"""
Swiggy Food Ordering Agent for Zoovy.
Handles restaurant food orders, cuisine searches, menu item discovery,
and cart population using the official Swiggy Food MCP Server.
Strictly adheres to 'Add-to-Cart Only' and Human-in-the-Loop order confirmation.
"""

from typing import Dict, Any, List, Optional
from rich.console import Console
from rich.panel import Panel

from zoovy.core.llm import OllamaClient
from zoovy.core.mcp_client import SwiggyFoodMCPClient
from zoovy.core.safety import PaymentGatekeeper, OrderCheckoutReview, CartItemSummary
from zoovy.agents.delivery.swiggy_metadata import SwiggyMetadataAgent

console = Console()


class SwiggyFoodAgent:
    """
    Dedicated AI Agent for Swiggy Food restaurant ordering.
    """

    SYSTEM_PROMPT = """You are Zoovy's Swiggy Food Specialist Agent.
Your job is to analyze food, meal, cuisine, or restaurant requests and extract:
1. Target dish or cuisine search terms
2. Quantity for each item
3. Cuisine preference or restaurant type

Respond with a JSON object:
{
  "restaurant_search": "e.g. Biryani or Meghana Foods",
  "items": [
    {"name": "Chicken Biryani", "quantity": 2, "notes": "spicy"}
  ],
  "address_preference": "Home"
}
"""

    def __init__(self, llm_client: OllamaClient, metadata_agent: Optional[SwiggyMetadataAgent] = None):
        self.llm = llm_client
        self.mcp = SwiggyFoodMCPClient()
        self.metadata_agent = metadata_agent or SwiggyMetadataAgent()

    def parse_food_intent(self, prompt: str) -> Dict[str, Any]:
        """Parses natural language food request using local LLM."""
        messages = [
            {"role": "system", "content": self.SYSTEM_PROMPT},
            {"role": "user", "content": f"Food Request: {prompt}"}
        ]
        parsed = self.llm.chat_structured(messages, schema={})
        if not parsed.get("items"):
            # Fallback heuristic
            parsed = {
                "restaurant_search": prompt.split()[0] if prompt else "Restaurant",
                "items": [{"name": prompt, "quantity": 1}],
                "address_preference": "Home"
            }
        return parsed

    def execute_food_order(
        self,
        prompt: str,
        web_context: Optional[str] = None,
        address_override: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Executes end-to-end food ordering:
        1. Verifies delivery address (prompts if missing)
        2. Discovers restaurant & dishes via Swiggy Food MCP
        3. Adds items to cart (ADD TO CART ONLY)
        4. Halts for human confirmation before placing order
        """
        console.print(f"\n[bold cyan]🍽️ [Swiggy Food Agent][/bold cyan] Processing order: [bold]'{prompt}'[/bold]")

        # 1. Address Resolution
        addr_record = self.metadata_agent.resolve_or_prompt_address(preferred_tag=address_override)
        delivery_address = addr_record.get("formatted", "Bengaluru - 560066")

        # 2. Parse Intent with Web Context
        augmented_prompt = prompt
        if web_context:
            augmented_prompt += f"\n[Web Context Reference:\n{web_context}]"

        intent = self.parse_food_intent(augmented_prompt)
        rest_query = intent.get("restaurant_search", "Restaurant")

        # 3. Discover Restaurants via MCP
        restaurants = self.mcp.search_restaurants(
            query=rest_query,
            latitude=addr_record.get("latitude", 12.9716),
            longitude=addr_record.get("longitude", 77.5946)
        )
        selected_rest = restaurants[0] if restaurants else {
            "restaurant_id": "sw_rest_default",
            "name": f"{rest_query.title()} Corner",
            "area": addr_record.get("city", "Bengaluru")
        }

        console.print(f"[green]✓ Selected Restaurant:[/green] [bold yellow]{selected_rest.get('name')}[/bold yellow] ({selected_rest.get('area', '')})")

        # 4. Search & Add Items to Cart (ADD TO CART ONLY)
        self.mcp.clear_cart()
        cart_summaries: List[CartItemSummary] = []

        for item_req in intent.get("items", []):
            name = item_req.get("name", "Dish")
            qty = int(item_req.get("quantity", 1))

            dishes = self.mcp.search_dishes(query=name, restaurant_id=selected_rest.get("restaurant_id"))
            dish = dishes[0] if dishes else {
                "dish_id": f"dish_{abs(hash(name)) % 1000}",
                "name": name.title(),
                "price_inr": 250.0,
                "description": f"Freshly made {name.title()}"
            }

            unit_price = float(dish.get("price_inr", 250.0))
            # Strict Add to Cart via MCP
            self.mcp.add_to_cart(
                restaurant_id=selected_rest.get("restaurant_id", "rest_01"),
                dish_id=dish.get("dish_id", "dish_01"),
                dish_name=dish.get("name", name),
                unit_price=unit_price,
                quantity=qty
            )

            cart_summaries.append(CartItemSummary(
                name=dish.get("name", name),
                variant=selected_rest.get("name", "Restaurant Special"),
                description=dish.get("description", f"Authentic {dish.get('name')}"),
                quantity=qty,
                unit_price_inr=unit_price,
                total_price_inr=unit_price * qty
            ))

        # 5. Fetch Cart Bill Summary
        cart_state = self.mcp.get_cart()
        subtotal = cart_state.get("subtotal", 0.0)
        delivery_fee = cart_state.get("delivery_fee", 35.0)
        taxes = cart_state.get("gst_taxes", 0.0)
        total_payable = cart_state.get("grand_total", subtotal + delivery_fee + taxes)

        # 6. Safety Gate: Itemized Invoice & Confirmation Required
        review = OrderCheckoutReview(
            platform="swiggy",
            store_name=f"{selected_rest.get('name')} (Swiggy Food MCP)",
            delivery_address=f"{addr_record.get('tag', 'Home')} - {delivery_address}",
            available_addresses=[f"{t} - {a.get('formatted')}" for t, a in self.metadata_agent.get_addresses().items()],
            items=cart_summaries,
            subtotal_inr=subtotal,
            delivery_fee_inr=delivery_fee + taxes,
            total_payable_inr=total_payable
        )

        console.print(f"\n[bold yellow]🛡️ Human Confirmation Required Before Order Placement[/bold yellow]")
        decision = PaymentGatekeeper.prompt_user_confirmation(review)

        if decision == "confirm":
            console.print(f"\n[bold green]✓ Swiggy Food Order Confirmed by User![/bold green]")
            payment_link = f"upi://pay?pa=swiggy@icici&pn=Swiggy&am={total_payable:.2f}&cu=INR"
            console.print(Panel(
                f"[bold cyan]Scan UPI QR to complete payment:[/bold cyan]\n[bold yellow]{payment_link}[/bold yellow]\n\n"
                f"• Restaurant: {selected_rest.get('name')}\n"
                f"• Deliver to: {delivery_address}\n"
                f"• Total Amount: ₹{total_payable:.2f}",
                title="💳 Swiggy Food Checkout Approved",
                border_style="green"
            ))
            return {"status": "ORDER_PLACED", "payment_link": payment_link, "total": total_payable}
        else:
            console.print(f"\n[yellow]⏸️ Order held in cart. No payment was triggered.[/yellow]")
            return {"status": "HELD_IN_CART", "items_count": len(cart_summaries)}
