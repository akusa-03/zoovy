import json
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from zoovy.core.llm import OllamaClient
from zoovy.core.safety import CartItemSummary

console = Console()


@dataclass
class GoalContract:
    """Explicit verifiable contract generated from the user\'s natural language goal."""
    raw_prompt: str
    target_platform: str
    items: List[Dict[str, Any]]
    max_budget_inr: Optional[float]
    acceptance_criteria: List[str]
    negative_constraints: List[str]


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
        """Deconstruct user prompt into a formal verifiable goal contract."""
        messages = [
            {"role": "system", "content": self.GOAL_FORMULATION_PROMPT},
            {"role": "user", "content": f"User Request: '{prompt}'\nPlatform hint: {platform_hint or 'auto'}"}
        ]
        parsed = self.llm.chat_structured(messages, schema={})
        return GoalContract(
            raw_prompt=prompt,
            target_platform=parsed.get("target_platform", platform_hint or "swiggy"),
            items=parsed.get("items", []),
            max_budget_inr=parsed.get("max_budget_inr"),
            acceptance_criteria=parsed.get("acceptance_criteria", []),
            negative_constraints=parsed.get("negative_constraints", [])
        )

    def evaluate_cart_state(self, goal: GoalContract, current_items: List[CartItemSummary]) -> EvaluationReport:
        """
        Impartial verification step comparing actual cart against goal contract.
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

        messages = [
            {"role": "system", "content": self.EVALUATOR_PROMPT},
            {"role": "user", "content": user_content}
        ]
        eval_json = self.llm.chat_structured(messages, schema={})

        return EvaluationReport(
            satisfied=eval_json.get("satisfied", False),
            passed_criteria=eval_json.get("passed_criteria", []),
            failed_criteria=eval_json.get("failed_criteria", []),
            unwanted_items_found=eval_json.get("unwanted_items_found", []),
            reflection=eval_json.get("reflection", "No reflection generated."),
            corrective_actions=eval_json.get("corrective_actions", [])
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
