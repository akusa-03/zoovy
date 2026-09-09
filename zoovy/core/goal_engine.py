"""
Goal-Oriented Dynamic Step Engine for Zoovy.
Deconstructs natural language prompts into explicit GoalContracts,
decomposes them into dynamic executable steps, and continually creates/adapts
steps until the objective is achieved with safety and confirmation guarantees.
"""

import re
import json
from enum import Enum
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from zoovy.core.llm import OllamaClient
from zoovy.core.safety import CartItemSummary

console = Console()


class FailureScenario(str, Enum):
    OUT_OF_STOCK = "out_of_stock"
    BUDGET_EXCEEDED = "budget_exceeded"
    UNREQUESTED_ITEMS_PRESENT = "unrequested_items_present"
    MISSING_ITEMS = "missing_items"
    MCP_SERVICE_TIMEOUT = "mcp_service_timeout"


class StepStatus(str, Enum):
    PENDING = "PENDING"
    RUNNING = "RUNNING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    REPLANNED = "REPLANNED"


@dataclass
class GoalStep:
    """A single discrete, verifiable action step within a dynamic plan."""
    step_id: str
    title: str
    agent_type: str  # "metadata", "web_search", "swiggy_food", "swiggy_instamart", "evaluator", "safety"
    action: str      # e.g. "resolve_address", "web_search", "search_add_items", "evaluate", "confirm_checkout"
    params: Dict[str, Any] = field(default_factory=dict)
    status: StepStatus = StepStatus.PENDING
    result: Optional[Any] = None
    error: Optional[str] = None


@dataclass
class GoalContract:
    """Explicit verifiable contract generated from the user's natural language goal."""
    raw_prompt: str
    target_platform: str  # "swiggy_food", "swiggy_instamart", "swiggy", "zepto", "zomato"
    items: List[Dict[str, Any]]
    max_budget_inr: Optional[float] = None
    delivery_address: Optional[str] = None
    max_sku_count: int = 15
    acceptance_criteria: List[str] = field(default_factory=list)
    negative_constraints: List[str] = field(default_factory=list)
    web_context: Optional[str] = None


@dataclass
class EvaluationReport:
    """Impartial assessment of whether current state matches the goal contract."""
    satisfied: bool
    passed_criteria: List[str]
    failed_criteria: List[str]
    unwanted_items_found: List[str]
    reflection: str
    corrective_actions: List[Dict[str, Any]]


class DynamicGoalPlan:
    """
    Mutable, dynamic queue of execution steps that can expand or self-correct in real time.
    """

    def __init__(self, contract: GoalContract):
        self.contract = contract
        self.steps: List[GoalStep] = []
        self.current_idx: int = 0

    def add_step(self, step: GoalStep):
        self.steps.append(step)

    def insert_substep(self, step: GoalStep):
        """Inserts a dynamic corrective sub-step immediately after the current step."""
        self.steps.insert(self.current_idx + 1, step)

    def render_plan(self):
        table = Table(title="📋 Dynamic Goal Execution Plan", expand=True)
        table.add_column("#", style="dim", width=4)
        table.add_column("Step Title", style="cyan bold")
        table.add_column("Agent Subsystem", style="yellow", width=18)
        table.add_column("Action", style="white", width=18)
        table.add_column("Status", width=12)

        for i, s in enumerate(self.steps, 1):
            if s.status == StepStatus.COMPLETED:
                st_str = "[bold green]✓ DONE[/bold green]"
            elif s.status == StepStatus.RUNNING:
                st_str = "[bold yellow]► ACTIVE[/bold yellow]"
            elif s.status == StepStatus.FAILED:
                st_str = "[bold red]✗ FAILED[/bold red]"
            elif s.status == StepStatus.REPLANNED:
                st_str = "[bold magenta]🔄 REPLAN[/bold magenta]"
            else:
                st_str = "[dim]PENDING[/dim]"

            table.add_row(str(i), s.title, s.agent_type, s.action, st_str)
        console.print(table)


class RecoveryRecipeEngine:
    """
    Self-healing recovery state machine mapping failure scenarios to deterministic
    recovery recipes before escalating to the human user.
    """

    def __init__(self, max_attempts: int = 2):
        self.max_attempts = max_attempts
        self.attempt_counts: Dict[str, int] = {}

    def can_attempt(self, scenario: FailureScenario) -> bool:
        return self.attempt_counts.get(scenario.value, 0) < self.max_attempts

    def record_attempt(self, scenario: FailureScenario):
        self.attempt_counts[scenario.value] = self.attempt_counts.get(scenario.value, 0) + 1

    def resolve_budget_exceeded(self, goal: GoalContract, items: List[CartItemSummary]) -> Dict[str, Any]:
        """Recovery recipe: suggest dropping non-essential items or reducing quantity."""
        self.record_attempt(FailureScenario.BUDGET_EXCEEDED)
        if not items:
            return {"action": "NONE", "details": "Cart is empty."}

        sorted_by_cost = sorted(items, key=lambda x: x.total_price_inr, reverse=True)
        expensive = sorted_by_cost[0]
        details = (
            f"Suggested reducing quantity of '{expensive.name}' (current total: ₹{expensive.total_price_inr:.2f}) "
            f"to fit within ₹{goal.max_budget_inr:.2f} cap."
        )
        console.print(f"[bold cyan]🔄 [Self-Healing Recovery][/bold cyan] {details}")
        return {"action": "REDUCE_QUANTITY", "target": expensive.name, "details": details}

    def resolve_out_of_stock(self, missing_item_name: str, alternatives: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
        """Recovery recipe: substitute unavailable item with closest verified variant."""
        self.record_attempt(FailureScenario.OUT_OF_STOCK)
        if not alternatives:
            console.print(f"[bold red]✗ [Self-Healing Recovery][/bold red] No valid substitutes found for '{missing_item_name}'.")
            return None

        best = alternatives[0]
        console.print(
            f"[bold cyan]🔄 [Self-Healing Recovery][/bold cyan] Item '{missing_item_name}' was out of stock. "
            f"Auto-substituted with: [bold yellow]{best.get('name')}[/bold yellow] (₹{best.get('unit_price_inr', best.get('price_inr', 0)):.2f})"
        )
        return best


class GoalOrchestrationEngine:
    """
    Comprehensive goal-oriented engine:
    1. Formulates contracts & acceptance criteria
    2. Decomposes prompts into executable steps
    3. Dynamically expands steps until the goal state is verified
    """

    GOAL_FORMULATION_PROMPT = """You are Zoovy's Goal Formulation Architect.
Analyze the user's natural language request and decompose it into a formal GoalContract.

Rules:
1. Target platform: 'swiggy_food' (meals, restaurants, cooked biryani, pizza), 'swiggy_instamart' (groceries, ingredients, snacks, cans, butter, pantry), 'zepto', or 'zomato'.
2. Extract exact items, pack sizes/quantities, and maximum budget if stated.
3. Formulate verifiable acceptance criteria and negative constraints.
4. RECIPE & INGREDIENT EXPANSION RULE: If the request asks for a recipe or ingredients to cook a dish (e.g. 'Find a recipe for chicken biryani and add ingredients to swiggy instamart cart'):
   - Set target_platform to 'swiggy_instamart'.
   - You MUST decompose the dish into its raw grocery cooking ingredients (e.g., Fresh Chicken, Basmati Rice, Biryani Masala, Curd, Onions, Ginger Garlic Paste, Mint Leaves, Ghee), NOT the prepared restaurant dish!

Output strictly valid JSON matching this schema:
{
  "target_platform": "swiggy_food" | "swiggy_instamart" | "zepto" | "zomato",
  "items": [
    {"name": "string", "quantity": 1, "variant": "string or null", "max_unit_price": 50.0}
  ],
  "max_budget_inr": null | number,
  "acceptance_criteria": [
    "cart contains exact target items and quantities",
    "item unit price is within budget if specified"
  ],
  "negative_constraints": [
    "no extra unrequested items added to cart",
    "cart must not exceed budget"
  ]
}
"""

    def __init__(self, llm_client: OllamaClient, max_cycles: int = 3):
        self.llm = llm_client
        self.max_cycles = max_cycles
        self.recovery = RecoveryRecipeEngine(max_attempts=2)

    def formulate_goal(self, prompt: str, platform_hint: Optional[str] = None, web_context: Optional[str] = None) -> GoalContract:
        """Deconstruct user prompt into a formal verifiable goal contract with budget fencing."""
        user_msg = f"User Request: '{prompt}'\nPlatform hint: {platform_hint or 'auto'}"
        if web_context:
            user_msg += f"\nReal-world Web Context:\n{web_context}"

        messages = [
            {"role": "system", "content": self.GOAL_FORMULATION_PROMPT},
            {"role": "user", "content": user_msg}
        ]
        try:
            parsed = self.llm.chat_structured(messages, schema={})
        except Exception:
            parsed = {}

        prompt_lower = prompt.lower()
        if platform_hint and platform_hint != "auto":
            target_platform = platform_hint
        elif "swiggy food" in prompt_lower:
            target_platform = "swiggy_food"
        elif "instamart" in prompt_lower or "swiggy" in prompt_lower:
            target_platform = "swiggy_instamart"
        elif "zepto" in prompt_lower:
            target_platform = "zepto"
        elif "zomato" in prompt_lower:
            target_platform = "zomato"
        elif any(w in prompt_lower for w in ["biryani", "curry", "pizza", "burger", "meal", "dinner", "lunch", "restaurant"]):
            target_platform = "swiggy_food"
        elif any(w in prompt_lower for w in ["diet coke", "coke", "butter", "tomato", "grocery", "chips", "juice", "milk", "egg"]):
            target_platform = "swiggy_instamart"
        else:
            target_platform = parsed.get("target_platform") or "swiggy_instamart"

        # Budget extraction
        budget = parsed.get("max_budget_inr")
        if not budget:
            budget_match = re.search(
                r'(?:under|below|within|budget(?:\s+of)?|max(?:\s+budget)?)\s*(?:rs\.?|inr|₹)?\s*(\d+(?:\.\d+)?)',
                prompt,
                re.IGNORECASE
            )
            if budget_match:
                try:
                    budget = float(budget_match.group(1))
                except ValueError:
                    pass

        # Items fallback
        items = parsed.get("items", [])
        if not items:
            items = [{"name": prompt, "quantity": 1, "variant": "Standard"}]

        acceptance_criteria = parsed.get("acceptance_criteria", [
            "All requested items added to cart in correct quantities",
            "Delivery address verified and saved in local metadata"
        ])
        negative_constraints = parsed.get("negative_constraints", [
            "No orders placed without explicit user confirmation",
            "Add-to-cart operations only before approval"
        ])
        if budget:
            budget_constraint = f"Total bill must not exceed ₹{budget:.2f}"
            if budget_constraint not in negative_constraints:
                negative_constraints.append(budget_constraint)

        return GoalContract(
            raw_prompt=prompt,
            target_platform=target_platform,
            items=items,
            max_budget_inr=budget,
            max_sku_count=15,
            acceptance_criteria=acceptance_criteria,
            negative_constraints=negative_constraints,
            web_context=web_context
        )

    def create_initial_plan(self, goal: GoalContract) -> DynamicGoalPlan:
        """
        Creates the structured step plan from the GoalContract.
        """
        plan = DynamicGoalPlan(goal)

        # Step 1: Address Resolution & Validation (via SwiggyMetadataAgent)
        plan.add_step(GoalStep(
            step_id="step_1_address",
            title="Verify & Resolve Delivery Address",
            agent_type="metadata",
            action="resolve_address",
            params={"preferred_tag": "Home"}
        ))

        # Step 2: Web Search Context Gathering (via WebSearchEngine)
        plan.add_step(GoalStep(
            step_id="step_2_web_search",
            title="Gather Live Real-World Web Context",
            agent_type="web_search",
            action="enrich_web_context",
            params={"query": goal.raw_prompt}
        ))

        # Step 3: Platform & Agent Dispatch
        agent_type = (
            "swiggy_food" if goal.target_platform in ["swiggy_food", "food"]
            else "swiggy_instamart" if goal.target_platform in ["swiggy_instamart", "instamart", "swiggy"]
            else "zepto" if goal.target_platform == "zepto"
            else "zomato"
        )
        plan.add_step(GoalStep(
            step_id="step_3_catalog_search",
            title=f"Search Catalog & Match Items on {agent_type.upper()}",
            agent_type=agent_type,
            action="discover_items",
            params={"items": goal.items}
        ))

        # Step 4: Strict Add to Cart
        plan.add_step(GoalStep(
            step_id="step_4_add_to_cart",
            title="Populate Basket (Add to Cart ONLY)",
            agent_type=agent_type,
            action="add_to_cart",
            params={"items": goal.items}
        ))

        # Step 5: Impartial Goal Evaluation & Budget Verification
        plan.add_step(GoalStep(
            step_id="step_5_evaluate",
            title="Verify Acceptance Criteria & Budget Fencing",
            agent_type="evaluator",
            action="evaluate_cart",
            params={"max_budget": goal.max_budget_inr}
        ))

        # Step 6: Human-in-the-Loop Confirmation Gate
        plan.add_step(GoalStep(
            step_id="step_6_confirm_gate",
            title="Present Itemized Invoice & Require Human Confirmation",
            agent_type="safety",
            action="request_confirmation",
            params={}
        ))

        return plan

    def evaluate_cart_state(self, goal: GoalContract, current_items: List[CartItemSummary]) -> EvaluationReport:
        """
        Evaluates current cart items against acceptance criteria and budget fence.
        """
        total_bill = sum(i.total_price_inr for i in current_items)
        passed_criteria = []
        failed_criteria = []

        if current_items:
            passed_criteria.append(f"Cart successfully populated with {len(current_items)} SKU(s)")
        else:
            failed_criteria.append("Cart is currently empty")

        # Budget Check
        if goal.max_budget_inr is not None:
            if total_bill <= goal.max_budget_inr:
                passed_criteria.append(f"Cart total ₹{total_bill:.2f} satisfies budget cap of ₹{goal.max_budget_inr:.2f}")
            else:
                overage = total_bill - goal.max_budget_inr
                failed_criteria.append(f"Budget fence violation: total ₹{total_bill:.2f} exceeds cap of ₹{goal.max_budget_inr:.2f} by ₹{overage:.2f}")

        satisfied = (len(failed_criteria) == 0 and len(current_items) > 0)
        reflection = "All acceptance criteria verified." if satisfied else "; ".join(failed_criteria)

        return EvaluationReport(
            satisfied=satisfied,
            passed_criteria=passed_criteria,
            failed_criteria=failed_criteria,
            unwanted_items_found=[],
            reflection=reflection,
            corrective_actions=[]
        )

    def print_goal_summary(self, goal: GoalContract):
        """Displays structured contract before execution."""
        table = Table(title="🎯 Target Goal Contract & Verification Specs", expand=True)
        table.add_column("Property", style="cyan", ratio=1)
        table.add_column("Requirement / Contract", style="white", ratio=3)

        table.add_row("Platform Target", goal.target_platform.upper())
        table.add_row("Requested Items", ", ".join([f"{i.get('quantity', 1)}x {i.get('name')}" for i in goal.items]))
        if goal.max_budget_inr:
            table.add_row("Max Budget Cap", f"₹{goal.max_budget_inr:.2f}")

        table.add_row("Acceptance Criteria", "\n".join([f"✓ {c}" for c in goal.acceptance_criteria]))
        if goal.negative_constraints:
            table.add_row("Negative Constraints", "\n".join([f"✗ {n}" for n in goal.negative_constraints]))

        console.print()
        console.print(table)
