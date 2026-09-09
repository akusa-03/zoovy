"""
Autonomous Delivery Orchestrator for Zoovy.
Integrates:
1. Zero-API-key Web Search Context Enrichment on every query
2. Goal-Based Dynamic Multi-Step Execution Loop
3. Official Swiggy MCP Server Client & Specialized Agents (Swiggy Food & Swiggy Instamart)
4. Swiggy Metadata Agent (Address storage in ~/.zoovy/swiggy_metadata.json)
5. Strict 'Add-to-Cart Only' and Human-in-the-Loop Confirmation Gate
"""

import sys
import time
from typing import Optional, List, Dict, Any
from rich.console import Console
from rich.panel import Panel

from zoovy.core.llm import OllamaClient
from zoovy.core.web_search import WebSearchEngine
from zoovy.core.safety import PaymentGatekeeper, OrderCheckoutReview, CartItemSummary
from zoovy.core.goal_engine import (
    GoalOrchestrationEngine,
    GoalContract,
    DynamicGoalPlan,
    GoalStep,
    StepStatus,
    RecoveryRecipeEngine,
    FailureScenario,
)
from zoovy.core.mcp_client import (
    SwiggyFoodMCPClient,
    SwiggyInstamartMCPClient,
    ZeptoMCPClient,
    ZomatoMCPClient
)
from zoovy.agents.delivery.swiggy_metadata import SwiggyMetadataAgent
from zoovy.agents.delivery.swiggy_food import SwiggyFoodAgent
from zoovy.agents.delivery.swiggy_instamart import SwiggyInstamartAgent

console = Console()


class DeliveryAgent:
    """
    Master Delivery Agent orchestrating:
    - WebSearchEngine for real-world context
    - SwiggyMetadataAgent for address storage in JSON
    - GoalOrchestrationEngine for dynamic step generation
    - Specialized Swiggy Food and Swiggy Instamart MCP agents
    """

    def __init__(self, llm_client: OllamaClient):
        self.llm = llm_client
        self.metadata_agent = SwiggyMetadataAgent()
        self.goal_engine = GoalOrchestrationEngine(self.llm)
        self.food_agent = SwiggyFoodAgent(self.llm, metadata_agent=self.metadata_agent)
        self.instamart_agent = SwiggyInstamartAgent(self.llm, metadata_agent=self.metadata_agent)

    def parse_request(self, user_prompt: str, default_platform: Optional[str] = None):
        """Extract structured OrderIntent for compatibility with legacy test harness."""
        from zoovy.agents.delivery.schemas import OrderIntent
        system_prompt = """You are Zoovy's Delivery Intelligence Agent.
Your task is to parse the user's natural language request into a strict JSON OrderIntent.
Supported platforms: 'zepto', 'swiggy', 'zomato'.

Output JSON schema:
{
  "platform": "zepto" | "swiggy" | "zomato",
  "items": [
    {"query": "search keyword", "quantity": integer, "preferred_variant": "string"}
  ],
  "address_preference": "Home"
}
"""
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": f"Request: {user_prompt}\nDefault platform hint: {default_platform or 'auto'}"}
        ]
        parsed_json = self.llm.chat_structured(messages, schema={})
        return OrderIntent(**parsed_json)

    def execute_order(self, prompt: str, platform_override: Optional[str] = None, use_browser: bool = False):
        """
        Executes end-to-end goal-oriented delivery workflow with dynamic multi-step planning.
        """
        console.print(f"\n[bold cyan]🚀 Zoovy Autonomous Goal Engine Initiated[/bold cyan]")
        console.print(f"[bold]Target Prompt:[/bold] '{prompt}'\n")

        # Step A: Live Web Search Context Enrichment on Every Query
        web_info = WebSearchEngine.enrich_query_context(prompt)
        web_context = web_info.get("context_summary", "")

        # Step B: Goal Contract Formulation
        contract = self.goal_engine.formulate_goal(
            prompt=prompt,
            platform_hint=platform_override,
            web_context=web_context
        )
        self.goal_engine.print_goal_summary(contract)

        # Step C: Dynamic Multi-Step Execution Plan
        plan = self.goal_engine.create_initial_plan(contract)
        plan.render_plan()

        # Step D: Execute Dynamic Step Loop
        delivery_address_record = None
        cart_items: List[CartItemSummary] = []
        payment_link = ""

        plan.current_idx = 0
        while plan.current_idx < len(plan.steps):
            step = plan.steps[plan.current_idx]
            step.status = StepStatus.RUNNING
            console.print(f"\n[bold yellow]► Executing Step {plan.current_idx + 1}/{len(plan.steps)}:[/bold yellow] [bold]{step.title}[/bold]")

            # 1. Action: resolve_address
            if step.action == "resolve_address":
                delivery_address_record = self.metadata_agent.resolve_or_prompt_address(
                    preferred_tag=step.params.get("preferred_tag")
                )
                contract.delivery_address = delivery_address_record.get("formatted")
                step.status = StepStatus.COMPLETED
                step.result = contract.delivery_address

            # 2. Action: enrich_web_context
            elif step.action == "enrich_web_context":
                step.status = StepStatus.COMPLETED
                step.result = web_context

            # 3. Action: discover_items & add_to_cart
            elif step.action in ["discover_items", "add_to_cart"]:
                # Check target agent
                if contract.target_platform == "swiggy_food":
                    console.print(f"[cyan]Dispatching to specialized Swiggy Food Agent...[/cyan]")
                    res = self.food_agent.execute_food_order(
                        prompt=prompt,
                        web_context=web_context,
                        address_override=delivery_address_record.get("tag") if delivery_address_record else None,
                        items_override=contract.items
                    )
                    step.status = StepStatus.COMPLETED
                    step.result = res
                    # Food agent already handled confirmation gate and itemization
                    return res

                elif contract.target_platform in ["swiggy_instamart", "swiggy"]:
                    console.print(f"[cyan]Dispatching to specialized Swiggy Instamart Agent...[/cyan]")
                    res = self.instamart_agent.execute_instamart_order(
                        prompt=prompt,
                        web_context=web_context,
                        address_override=delivery_address_record.get("tag") if delivery_address_record else None,
                        items_override=contract.items
                    )
                    step.status = StepStatus.COMPLETED
                    step.result = res
                    # Instamart agent already handled confirmation gate and itemization
                    return res

                elif contract.target_platform == "zepto":
                    mcp = ZeptoMCPClient()
                    cart_items = []
                    for it in contract.items:
                        name = it.get("name", "Item")
                        qty = it.get("quantity", 1)
                        results = mcp.search_products(name)
                        prod = results[0] if results else {"name": name, "unit_price_inr": 50.0, "variant": "Standard"}
                        mcp.add_to_cart(prod.get("name", name), quantity=qty)
                        unit_p = float(prod.get("unit_price_inr", 50.0))
                        cart_items.append(CartItemSummary(
                            name=prod.get("name", name),
                            variant=prod.get("variant", "Standard"),
                            description=f"Zepto Dark Store: {prod.get('name')}",
                            quantity=qty,
                            unit_price_inr=unit_p,
                            total_price_inr=unit_p * qty
                        ))
                    step.status = StepStatus.COMPLETED
                    step.result = cart_items

                else:  # Zomato fallback
                    mcp = ZomatoMCPClient()
                    cart_items = []
                    for it in contract.items:
                        name = it.get("name", "Dish")
                        qty = it.get("quantity", 1)
                        results = mcp.search_dishes(name)
                        prod = results[0] if results else {"name": name, "price_inr": 250.0}
                        unit_p = float(prod.get("price_inr", 250.0))
                        cart_items.append(CartItemSummary(
                            name=prod.get("name", name),
                            variant="Standard",
                            description=f"Restaurant Dish: {prod.get('name')}",
                            quantity=qty,
                            unit_price_inr=unit_p,
                            total_price_inr=unit_p * qty
                        ))
                    step.status = StepStatus.COMPLETED
                    step.result = cart_items

            # 4. Action: evaluate_cart
            elif step.action == "evaluate_cart":
                eval_report = self.goal_engine.evaluate_cart_state(contract, cart_items)
                if eval_report.satisfied:
                    console.print("[bold green]✓ Acceptance Criteria Satisfied:[/bold green] All goal constraints met.")
                    step.status = StepStatus.COMPLETED
                else:
                    console.print(f"[yellow]⚠ Evaluation Notes:[/yellow] {eval_report.reflection}")
                    # Dynamic Step Generation: Insert corrective step if budget was breached
                    if contract.max_budget_inr and sum(i.total_price_inr for i in cart_items) > contract.max_budget_inr:
                        console.print("[magenta]🔄 Dynamically inserting step: Auto-Reduce Quantities to meet budget[/magenta]")
                        corrective_step = GoalStep(
                            step_id=f"step_dynamic_budget_{plan.current_idx}",
                            title="Auto-Adjust Quantities for Budget Fence",
                            agent_type="evaluator",
                            action="adjust_budget_fence"
                        )
                        plan.insert_substep(corrective_step)
                    step.status = StepStatus.REPLANNED

            # 5. Action: adjust_budget_fence (Dynamic sub-step)
            elif step.action == "adjust_budget_fence":
                self.goal_engine.recovery.resolve_budget_exceeded(contract, cart_items)
                step.status = StepStatus.COMPLETED

            # 6. Action: request_confirmation (HITL Confirmation Gate)
            elif step.action == "request_confirmation":
                subtotal = sum(i.total_price_inr for i in cart_items)
                del_fee = 25.0
                review = OrderCheckoutReview(
                    platform=contract.target_platform,
                    store_name=f"{contract.target_platform.capitalize()} MCP Hub",
                    delivery_address=contract.delivery_address or "Home: Bengaluru",
                    available_addresses=[f"{t} - {a.get('formatted')}" for t, a in self.metadata_agent.get_addresses().items()],
                    items=cart_items,
                    subtotal_inr=subtotal,
                    delivery_fee_inr=del_fee,
                    total_payable_inr=subtotal + del_fee
                )
                console.print(f"\n[bold yellow]🛡️ Human Confirmation Required Before Order Placement[/bold yellow]")
                decision = PaymentGatekeeper.prompt_user_confirmation(review)
                if decision == "confirm":
                    step.status = StepStatus.COMPLETED
                    console.print(f"\n[bold green]✓ Order Confirmed by User![/bold green]")
                    payment_link = f"upi://pay?pa={contract.target_platform}@icici&pn=Zoovy&am={subtotal+del_fee:.2f}&cu=INR"
                    console.print(Panel(
                        f"[bold cyan]Scan UPI QR to complete payment:[/bold cyan]\n[bold yellow]{payment_link}[/bold yellow]\n\n"
                        f"• Platform: {contract.target_platform.upper()}\n"
                        f"• Deliver to: {contract.delivery_address}\n"
                        f"• Total Amount: ₹{subtotal + del_fee:.2f}",
                        title="💳 Checkout Approved",
                        border_style="green"
                    ))
                else:
                    step.status = StepStatus.COMPLETED
                    console.print(f"\n[yellow]⏸️ Order kept in cart. No payment was triggered.[/yellow]")

            plan.current_idx += 1

        console.print(f"\n[bold green]✓ Dynamic Goal Plan Execution Complete![/bold green]")
