"""
Swiggy Instamart Grocery & Quick-Commerce Agent for Zoovy.
Handles dark-store grocery, snack, beverage, and essentials ordering
via the official Swiggy Instamart MCP Server.
Enforces 'Add-to-Cart Only' and Human-in-the-Loop payment confirmation.
"""

from typing import Dict, Any, List, Optional
from rich.console import Console
from rich.panel import Panel

from zoovy.core.llm import OllamaClient
from zoovy.core.mcp_client import SwiggyInstamartMCPClient
from zoovy.core.safety import PaymentGatekeeper, OrderCheckoutReview, CartItemSummary
from zoovy.agents.delivery.swiggy_metadata import SwiggyMetadataAgent

console = Console()


class SwiggyInstamartAgent:
    """
    Dedicated AI Agent for Swiggy Instamart quick-commerce grocery ordering.
    """

    SYSTEM_PROMPT = """You are Zoovy's Swiggy Instamart Grocery Specialist Agent.
Your job is to analyze grocery, snack, drink, and pantry requests and extract:
1. Target grocery items and search queries
2. Specific pack sizes / variants (e.g. 500g, 1kg, 300ml)
3. Exact quantity for each item

Respond with a JSON object:
{
  "items": [
    {"query": "diet coke", "quantity": 4, "variant": "300 ml"},
    {"query": "amul butter", "quantity": 1, "variant": "500 g"}
  ],
  "address_preference": "Home"
}
"""

    def __init__(self, llm_client: OllamaClient, metadata_agent: Optional[SwiggyMetadataAgent] = None):
        self.llm = llm_client
        self.mcp = SwiggyInstamartMCPClient()
        self.metadata_agent = metadata_agent or SwiggyMetadataAgent()

    def parse_instamart_intent(self, prompt: str) -> Dict[str, Any]:
        """Parses grocery request using local LLM."""
        messages = [
            {"role": "system", "content": self.SYSTEM_PROMPT},
            {"role": "user", "content": f"Grocery Request: {prompt}"}
        ]
        parsed = self.llm.chat_structured(messages, schema={})
        if not parsed.get("items"):
            # Fallback heuristic
            parsed = {
                "items": [{"query": prompt, "quantity": 1, "variant": "Standard"}],
                "address_preference": "Home"
            }
        return parsed

    def execute_instamart_order(
        self,
        prompt: str,
        web_context: Optional[str] = None,
        address_override: Optional[str] = None,
        items_override: Optional[List[Dict[str, Any]]] = None,
        selected_address: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Executes end-to-end Instamart grocery ordering:
        1. Always asks for Swiggy OAuth and fetches cloud addresses for user selection
        2. Discovers items via Swiggy Instamart MCP
        3. Adds items to cart (ADD TO CART ONLY)
        4. Halts for human confirmation before placing order
        """
        console.print(f"\n[bold cyan]🛒 [Swiggy Instamart Agent][/bold cyan] Processing grocery order: [bold]'{prompt}'[/bold]")

        # 1. Address Resolution via Swiggy OAuth
        if selected_address:
            addr_record = selected_address
        else:
            addr_record = self.metadata_agent.resolve_or_prompt_address(preferred_tag=address_override, force_oauth=True)
        delivery_address = addr_record.get("formatted", "Bengaluru - 560066")

        # 2. Parse Intent with Web Context or use items_override from Goal Contract
        if items_override:
            items_to_add = items_override
        else:
            augmented_prompt = prompt
            if web_context:
                augmented_prompt += f"\n[Web Context Reference:\n{web_context}]"
            intent = self.parse_instamart_intent(augmented_prompt)
            items_to_add = intent.get("items", [])

        # 3. Search & Add Items to Cart (ADD TO CART ONLY)
        self.mcp.clear_cart()
        cart_summaries: List[CartItemSummary] = []

        for item_req in items_to_add:
            q = item_req.get("query") or item_req.get("name") or "Item"
            qty = int(item_req.get("quantity", 1))
            preferred_var = item_req.get("variant", "Standard")

            products = self.mcp.search_items(query=q)
            prod = products[0] if products else {
                "product_id": f"im_{abs(hash(q)) % 1000}",
                "name": q.title(),
                "variant": preferred_var,
                "price_inr": 40.0,
                "description": f"Instamart Dark Store: {q.title()}"
            }

            unit_price = float(prod.get("price_inr", 40.0))
            variant_str = prod.get("variant", preferred_var)

            # Strict Add to Cart via MCP
            self.mcp.add_to_cart(
                product_id=prod.get("product_id", "prod_01"),
                item_name=prod.get("name", q),
                variant=variant_str,
                unit_price=unit_price,
                quantity=qty
            )

            cart_summaries.append(CartItemSummary(
                name=prod.get("name", q),
                variant=variant_str,
                description=prod.get("description", f"Instamart Dark Store item: {prod.get('name')}"),
                quantity=qty,
                unit_price_inr=unit_price,
                total_price_inr=unit_price * qty
            ))

        # 4. Fetch Cart Bill Summary
        cart_state = self.mcp.get_cart()
        subtotal = cart_state.get("subtotal", 0.0)
        delivery_fee = cart_state.get("delivery_fee", 25.0)
        total_payable = cart_state.get("grand_total", subtotal + delivery_fee)

        # 5. Safety Gate: Itemized Invoice & Confirmation Required
        review = OrderCheckoutReview(
            platform="swiggy",
            store_name="Swiggy Instamart Dark Store (10-15 Min Pod)",
            delivery_address=f"{addr_record.get('tag', 'Home')} - {delivery_address}",
            available_addresses=[f"{t} - {a.get('formatted')}" for t, a in self.metadata_agent.get_addresses().items()],
            items=cart_summaries,
            subtotal_inr=subtotal,
            delivery_fee_inr=delivery_fee,
            total_payable_inr=total_payable
        )

        console.print(f"\n[bold yellow]🛡️ Human Confirmation Required Before Order Placement[/bold yellow]")
        decision = PaymentGatekeeper.prompt_user_confirmation(review)

        if decision == "confirm":
            console.print(f"\n[bold green]✓ Swiggy Instamart Order Confirmed by User![/bold green]")
            payment_link = f"upi://pay?pa=swiggy@icici&pn=SwiggyInstamart&am={total_payable:.2f}&cu=INR"
            console.print(Panel(
                f"[bold cyan]Scan UPI QR to complete payment:[/bold cyan]\n[bold yellow]{payment_link}[/bold yellow]\n\n"
                f"• Pod: Swiggy Instamart Dark Store (10-15 mins ETA)\n"
                f"• Deliver to: {delivery_address}\n"
                f"• Total Amount: ₹{total_payable:.2f}",
                title="💳 Swiggy Instamart Checkout Approved",
                border_style="green"
            ))
            return {"status": "ORDER_PLACED", "payment_link": payment_link, "total": total_payable}
        else:
            console.print(f"\n[yellow]⏸️ Order held in cart. No payment was triggered.[/yellow]")
            return {"status": "HELD_IN_CART", "items_count": len(cart_summaries)}
