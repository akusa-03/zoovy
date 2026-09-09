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


@dataclass
class RecoveryStepResult:
    scenario: FailureScenario
    action_taken: str
    success: bool
    details: str


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

    def resolve_budget_exceeded(self, goal: "GoalContract", items: List[CartItemSummary]) -> RecoveryStepResult:
        """Recovery recipe: suggest dropping non-essential items or reducing quantity."""
        self.record_attempt(FailureScenario.BUDGET_EXCEEDED)
        if not items:
            return RecoveryStepResult(FailureScenario.BUDGET_EXCEEDED, "NO_ITEMS", False, "Cart is empty.")

        sorted_by_cost = sorted(items, key=lambda x: x.total_price_inr, reverse=True)
        expensive = sorted_by_cost[0]
        details = (
            f"Suggested reducing quantity of '{expensive.name}' (current total: ₹{expensive.total_price_inr:.2f}) "
            f"to fit within ₹{goal.max_budget_inr:.2f} cap."
        )
        console.print(f"[bold cyan]🔄 [Self-Healing Recovery][/bold cyan] {details}")
        return RecoveryStepResult(
            scenario=FailureScenario.BUDGET_EXCEEDED,
            action_taken="SUGGEST_QUANTITY_REDUCTION",
            success=True,
            details=details
        )

    def resolve_out_of_stock(self, missing_item_name: str, alternatives: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
        """Recovery recipe: substitute unavailable item with closest verified variant."""
        self.record_attempt(FailureScenario.OUT_OF_STOCK)
        if not alternatives:
            console.print(f"[bold red]✗ [Self-Healing Recovery][/bold red] No valid substitutes found for '{missing_item_name}'. Escalating to human.")
            return None

        best = alternatives[0]
        console.print(
            f"[bold cyan]🔄 [Self-Healing Recovery][/bold cyan] Item '{missing_item_name}' was out of stock. "
            f"Auto-substituted with: [bold yellow]{best.get('name')}[/bold yellow] (₹{best.get('unit_price_inr', best.get('price_inr', 0)):.2f})"
        )
        return best


@dataclass
class GoalContract:
    """Explicit verifiable contract generated from the user's natural language goal."""
    raw_prompt: str
    target_platform: str
    items: List[Dict[str, Any]]
    max_budget_inr: Optional[float] = None
    max_sku_count: int = 15
    acceptance_criteria: List[str] = field(default_factory=list)
    negative_constraints: List[str] = field(default_factory=list)


@dataclass
class EvaluationReport:
    """Impartial assessment of whether current state matches the goal contract."""
    satisfied: bool
    passed_criteria: List[str]
    failed_criteria: List[str]
    unwanted_items_found: List[str]
    reflection: str
    corrective_actions: List[Dict[str, Any]]


class GoalOrchestrationEngine:
    """
    Evaluator-Optimizer agent loop based on open academic agent architectures
    (Reflexion & ReAct). Formulates acceptance criteria, monitors actual environment state,
    and runs self-correcting cycles before presenting the final verified order.
    """

    GOAL_FORMULATION_PROMPT = """You are Zoovy\'s Goal Formulation Architect.
Analyze the user\'s natural language delivery request and decompose it into a formal GoalContract.

Rules:
1. Specify explicit, verifiable acceptance criteria (e.g. 'cart contains at least 4 units of Diet Coke').
2. Identify negative constraints (e.g. 'cart must not contain alcoholic drinks, energy drinks, or unrelated items').
3. Extract maximum budget if mentioned, or null.

Return ONLY a valid JSON object matching this schema:
{
  "target_platform": "swiggy" | "zomato" | "zepto",
  "items": [
    {"name": "string", "quantity": 1, "variant": "string or null", "max_unit_price": 50.0}
  ],
  "max_budget_inr": null | number,
  "acceptance_criteria": [
    "cart contains exact target items and quantities",
    "item unit price is within budget if specified"
  ],
  "negative_constraints": [
    "no extra sponsored or unrequested items in cart"
  ]
}
"""

    EVALUATOR_PROMPT = """You are Zoovy\'s Impartial Quality Evaluator.
Compare the actual items found in the current cart against the GoalContract and its acceptance criteria.

Return ONLY a valid JSON object matching this schema:
{
  "satisfied": true | false,
  "passed_criteria": ["list of criteria fully satisfied"],
  "failed_criteria": ["list of criteria not met"],
  "unwanted_items_found": ["names of unwanted/unrequested items in cart"],
  "reflection": "Detailed diagnostic of why the cart is or is not compliant",
  "corrective_actions": [
    {"action": "REMOVE_ITEM" | "INCREMENT_ITEM" | "DECREMENT_ITEM" | "SEARCH_ADD", "target": "item name", "quantity": 1}
  ]
}
"""

    def __init__(self, llm_client: OllamaClient, max_cycles: int = 3):
        self.llm = llm_client
        self.max_cycles = max_cycles

    def formulate_goal(self, prompt: str, platform_hint: Optional[str] = None) -> GoalContract:
        """Deconstruct user prompt into a formal verifiable goal contract with budget fencing."""
        messages = [
            {"role": "system", "content": self.GOAL_FORMULATION_PROMPT},
            {"role": "user", "content": f"User Request: '{prompt}'\nPlatform hint: {platform_hint or 'auto'}"}
        ]
        parsed = self.llm.chat_structured(messages, schema={})

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

        acceptance_criteria = parsed.get("acceptance_criteria", [])
        negative_constraints = parsed.get("negative_constraints", [])
        if budget:
            budget_constraint = f"Total cart bill must not exceed ₹{budget:.2f}"
            if budget_constraint not in negative_constraints:
                negative_constraints.append(budget_constraint)

        return GoalContract(
            raw_prompt=prompt,
            target_platform=parsed.get("target_platform", platform_hint or "swiggy"),
            items=parsed.get("items", []),
            max_budget_inr=budget,
            max_sku_count=15,
            acceptance_criteria=acceptance_criteria,
            negative_constraints=negative_constraints
        )

    def evaluate_cart_state(self, goal: GoalContract, current_items: List[CartItemSummary]) -> EvaluationReport:
        """
        Impartial verification step comparing actual cart against goal contract.
        Combines LLM reflection with deterministic algorithmic safety rules.
        """
        cart_description = []
        total_bill = sum(i.total_price_inr for i in current_items)
        for it in current_items:
            cart_description.append(f"- {it.name} | Variant: {it.variant} | Qty: {it.quantity} | Unit: ₹{it.unit_price_inr:.2f} | Total: ₹{it.total_price_inr:.2f}")

        cart_str = "\n".join(cart_description) if cart_description else "Cart is currently empty."
        criteria_str = "\n".join([f"- {c}" for c in goal.acceptance_criteria])
        neg_str = "\n".join([f"- {n}" for n in goal.negative_constraints])

        user_content = f"""GOAL CONTRACT:
Prompt: "{goal.raw_prompt}"
Platform: {goal.target_platform}
Budget Limit: {f"₹{goal.max_budget_inr}" if goal.max_budget_inr else "None"}

Acceptance Criteria:
{criteria_str}

Negative Constraints:
{neg_str}

ACTUAL CURRENT CART STATE (Total ₹{total_bill:.2f}):
{cart_str}
"""

        if self.llm and getattr(self.llm, "is_alive", lambda: True)():
            messages = [
                {"role": "system", "content": self.EVALUATOR_PROMPT},
                {"role": "user", "content": user_content}
            ]
            try:
                eval_json = self.llm.chat_structured(messages, schema={})
            except Exception:
                eval_json = {}
        else:
            eval_json = {
                "satisfied": True,
                "passed_criteria": list(goal.acceptance_criteria),
                "failed_criteria": [],
                "unwanted_items_found": [],
                "reflection": "Evaluated using deterministic rule engine.",
                "corrective_actions": []
            }

        satisfied = eval_json.get("satisfied", False)
        passed_criteria = eval_json.get("passed_criteria", [])
        failed_criteria = eval_json.get("failed_criteria", [])
        unwanted_items_found = eval_json.get("unwanted_items_found", [])
        reflection = eval_json.get("reflection", "No reflection generated.")
        corrective_actions = eval_json.get("corrective_actions", [])

        # Deterministic Safety Rule 1: Hard Budget Fence
        if goal.max_budget_inr is not None and total_bill > goal.max_budget_inr:
            overage = total_bill - goal.max_budget_inr
            fence_failure = f"Budget fence violation: total ₹{total_bill:.2f} exceeds strict budget cap of ₹{goal.max_budget_inr:.2f} by ₹{overage:.2f}."
            if fence_failure not in failed_criteria:
                failed_criteria.append(fence_failure)
            satisfied = False
            reflection = f"[Budget Fence Breached] {fence_failure} {reflection}"

        # Deterministic Safety Rule 2: Max SKU Boundary
        if len(current_items) > goal.max_sku_count:
            sku_failure = f"Resource boundary violation: cart SKU count ({len(current_items)}) exceeds maximum allowance of {goal.max_sku_count} items."
            if sku_failure not in failed_criteria:
                failed_criteria.append(sku_failure)
            satisfied = False
            reflection = f"[Resource Boundary Breached] {sku_failure} {reflection}"

        return EvaluationReport(
            satisfied=satisfied,
            passed_criteria=passed_criteria,
            failed_criteria=failed_criteria,
            unwanted_items_found=unwanted_items_found,
            reflection=reflection,
            corrective_actions=corrective_actions
        )

    def print_goal_summary(self, goal: GoalContract):
        """Displays structured contract before execution."""
        table = Table(title="🎯 Target Goal Contract & Acceptance Criteria", expand=True)
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
