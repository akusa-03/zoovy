"""
Comprehensive Test Suite for Zoovy Swiggy & Dynamic Goal Engine Features:
1. Web Search Context Retrieval on every query
2. Goal-Based Dynamic Step Generation Loop
3. Swiggy Metadata Agent (JSON persistence & missing address prompting)
4. Swiggy Food & Instamart MCP Clients (JSON-RPC tools/call)
5. Strict 'Add to Cart Only' and Confirmation-before-Order Gates
"""

import sys
import os
os.environ["ZOVI_TEST_MODE"] = "1"
from pathlib import Path
from rich.console import Console

from zoovy.core.llm import OllamaClient
from zoovy.core.web_search import WebSearchEngine
from zoovy.core.goal_engine import GoalOrchestrationEngine, GoalStep, StepStatus
from zoovy.core.mcp_client import SwiggyFoodMCPClient, SwiggyInstamartMCPClient
from zoovy.agents.delivery.swiggy_metadata import SwiggyMetadataAgent
from zoovy.agents.delivery.swiggy_food import SwiggyFoodAgent
from zoovy.agents.delivery.swiggy_instamart import SwiggyInstamartAgent
from zoovy.core.safety import CartItemSummary

console = Console(highlight=False)

def run_tests():
    # Preserve real user tokens
    token_dir = Path.home() / ".zoovy" / "tokens"
    token_backups = {}
    if token_dir.exists():
        for tf in token_dir.glob("*.json"):
            try:
                token_backups[tf.name] = tf.read_text(encoding="utf-8")
            except Exception:
                pass

    console.print("\n[bold cyan]═══════════════════════════════════════════════════════════════[/bold cyan]")
    console.print("[bold cyan]       SWIGGY MCP & GOAL ENGINE SYSTEM VERIFICATION            [/bold cyan]")
    # TEST 1: Web Search on Query
    console.print("[bold yellow]► TEST 1: Live Web Search Context Retrieval[/bold yellow]")
    res = WebSearchEngine.enrich_query_context("4 cans of diet coke 300ml")
    assert res is not None, "Web search result should not be None"
    assert "query" in res, "Should contain original query"
    console.print(f"  • Search Query Executed: [cyan]'{res['search_query']}'[/cyan]")
    console.print(f"  • Web References Retrieved: [green]{len(res['raw_results'])} items[/green]")
    console.print("  [bold green]✓ Web Search Engine PASSED[/bold green]\n")

    # TEST 2: Swiggy Metadata Agent (JSON Storage)
    console.print("[bold yellow]► TEST 2: Swiggy Metadata Agent (Address JSON Storage)[/bold yellow]")
    test_json_file = Path.home() / ".zoovy" / "test_swiggy_metadata.json"
    if test_json_file.exists():
        test_json_file.unlink()

    meta_agent = SwiggyMetadataAgent(metadata_file=test_json_file)
    assert not meta_agent.has_addresses(), "Should initially have no addresses"

    # Save test address
    meta = meta_agent.load_metadata()
    meta["addresses"]["Home"] = {
        "tag": "Home",
        "flat_no": "Flat 501",
        "address_line": "Palm Meadows, Whitefield",
        "city": "Bengaluru",
        "pincode": "560066",
        "formatted": "Flat 501, Palm Meadows, Whitefield, Bengaluru - 560066"
    }
    meta_agent.save_metadata(meta)

    assert meta_agent.has_addresses(), "Should have saved address"
    addr = meta_agent.get_address("Home")
    assert addr["pincode"] == "560066", "Pincode should match"
    console.print(f"  • JSON File Path: [cyan]{test_json_file}[/cyan]")
    console.print(f"  • Stored Address: [green]{addr['formatted']}[/green]")
    console.print("  [bold green]✓ Swiggy Metadata Agent PASSED[/bold green]\n")

    # TEST 3: Official Swiggy MCP Clients (Food & Instamart)
    console.print("[bold yellow]► TEST 3: Swiggy MCP Server Protocol Clients[/bold yellow]")
    food_mcp = SwiggyFoodMCPClient()
    im_mcp = SwiggyInstamartMCPClient()

    # Food MCP
    rests = food_mcp.search_restaurants("Biryani")
    assert len(rests) > 0, "Should find at least 1 restaurant"
    dishes = food_mcp.search_dishes("Chicken Biryani", restaurant_id=rests[0]["restaurant_id"])
    assert len(dishes) > 0, "Should find dishes"
    add_food_res = food_mcp.add_to_cart(rests[0]["restaurant_id"], dishes[0]["dish_id"], dishes[0]["name"], 320.0, 2)
    assert add_food_res["status"] == "SUCCESS", "Add to cart should succeed"
    food_cart = food_mcp.get_cart()
    assert food_cart["subtotal"] == 640.0, "Subtotal should equal 2 * 320"
    console.print(f"  • Swiggy Food MCP: Added '{dishes[0]['name']}' x2 (Subtotal: ₹{food_cart['subtotal']:.2f})")

    # Instamart MCP
    im_items = im_mcp.search_items("Diet Coke")
    assert len(im_items) > 0, "Should find items"
    add_im_res = im_mcp.add_to_cart(im_items[0]["product_id"], im_items[0]["name"], "300 ml", 40.0, 4)
    assert add_im_res["status"] == "SUCCESS", "Add to cart should succeed"
    im_cart = im_mcp.get_cart()
    assert im_cart["subtotal"] == 160.0, "Subtotal should equal 4 * 40"
    console.print(f"  • Swiggy Instamart MCP: Added '{im_items[0]['name']}' x4 (Subtotal: ₹{im_cart['subtotal']:.2f})")
    console.print("  [bold green]✓ Swiggy MCP Server Clients PASSED[/bold green]\n")

    # TEST 4: Goal-Oriented Dynamic Step Planning
    console.print("[bold yellow]► TEST 4: Dynamic Goal Engine & Step Decomposition[/bold yellow]")
    ollama = OllamaClient(model="qwen2.5:1.5b")
    engine = GoalOrchestrationEngine(ollama)
    contract = engine.formulate_goal(
        prompt="Order 4 cans of diet coke and 1 pack amul butter under 350 rs",
        web_context=res.get("context_summary")
    )
    assert contract.target_platform == "swiggy_instamart", f"Expected swiggy_instamart, got {contract.target_platform}"
    assert contract.max_budget_inr == 350.0, f"Expected 350.0 budget, got {contract.max_budget_inr}"

    plan = engine.create_initial_plan(contract)
    assert len(plan.steps) >= 5, "Plan should have at least 5 structured steps"
    
    # Test Dynamic Sub-Step Insertion
    substep = GoalStep(
        step_id="step_dynamic_substitute",
        title="Substitute Out-of-Stock Item",
        agent_type="swiggy_instamart",
        action="resolve_substitute"
    )
    plan.insert_substep(substep)
    assert plan.steps[1].step_id == "step_dynamic_substitute", "Dynamic sub-step should be inserted"
    console.print(f"  • Formulated Goal Platform: [green]{contract.target_platform.upper()}[/green]")
    console.print(f"  • Extracted Budget Fence: [green]₹{contract.max_budget_inr:.2f}[/green]")
    console.print(f"  • Dynamic Steps Formulated: [green]{len(plan.steps)} steps (with dynamic sub-step)[/green]")
    console.print("  [bold green]✓ Dynamic Goal Engine PASSED[/bold green]\n")

    # TEST 5: Strict Add-to-Cart Only & Budget Evaluation
    console.print("[bold yellow]► TEST 5: Cart Evaluation & Budget Fence Verification[/bold yellow]")
    test_cart = [
        CartItemSummary("Diet Coke Can", "300 ml", "Drink", 4, 40.0, 160.0),
        CartItemSummary("Amul Butter", "500 g", "Butter", 1, 275.0, 275.0),
    ]
    # Total = 435 > 350 budget
    eval_rep = engine.evaluate_cart_state(contract, test_cart)
    assert not eval_rep.satisfied, "Should fail budget fence of 350 when total is 435"
    assert any("Budget fence violation" in fc for fc in eval_rep.failed_criteria)
    console.print("  • Budget Fence Triggered: [green]Cart blocked at ₹435.00 > ₹350.00 cap[/green]")

    # Resolve with recovery recipe
    recovery_res = engine.recovery.resolve_budget_exceeded(contract, test_cart)
    assert recovery_res["action"] == "REDUCE_QUANTITY"
    console.print(f"  • Self-Healing Step: [green]{recovery_res['details']}[/green]")
    console.print("  [bold green]✓ Safety & Cart Fence Evaluation PASSED[/bold green]\n")

    # TEST 6: Swiggy OAuth & Cloud Address Selection
    console.print("[bold yellow]► TEST 6: Swiggy OAuth & Cloud Address Synchronization[/bold yellow]")
    cloud_addrs = food_mcp.fetch_cloud_addresses(token="test_swiggy_oauth_token")
    assert len(cloud_addrs) >= 3, "Should fetch at least 3 addresses from Swiggy cloud account"
    assert any(a["tag"] == "Home" for a in cloud_addrs), "Should contain Home address"
    assert any(a["tag"] == "Work" for a in cloud_addrs), "Should contain Work address"
    console.print(f"  • Fetched {len(cloud_addrs)} cloud addresses via Swiggy OAuth:")
    for ca in cloud_addrs:
        console.print(f"    - [{ca['tag']}] {ca['formatted']}")

    # Test address selection via metadata agent
    test_oauth_meta_file = Path.home() / ".zoovy" / "test_oauth_meta.json"
    if test_oauth_meta_file.exists():
        test_oauth_meta_file.unlink()
    oauth_agent = SwiggyMetadataAgent(metadata_file=test_oauth_meta_file)
    chosen = oauth_agent.prompt_swiggy_oauth_and_select_address(preferred_tag="Work")
    assert chosen is not None, "Chosen address should not be None"
    assert chosen["tag"] == "Work", "Should select preferred Work address"
    console.print(f"  • Selected Delivery Address: [green]{chosen['tag']} - {chosen['formatted']}[/green]")
    console.print("  [bold green]✓ Swiggy OAuth & Cloud Address Selection PASSED[/bold green]\n")

    # TEST 7: Swiggy OAuth 2.0 Browser Server & Callback Flow
    console.print("[bold yellow]► TEST 7: Swiggy OAuth 2.0 Browser Server & Callback Flow[/bold yellow]")
    import threading
    import requests
    from zoovy.core.oauth import SwiggyOAuthManager, SwiggyOAuthServer, SwiggyOAuthHandler

    port = SwiggyOAuthManager.get_free_port(8765)
    server = SwiggyOAuthServer(("127.0.0.1", port), SwiggyOAuthHandler)
    server_t = threading.Thread(target=server.serve_forever, daemon=True)
    server_t.start()

    try:
        # 1. Browser GET /oauth/login
        login_res = requests.get(f"http://127.0.0.1:{port}/oauth/login")
        assert login_res.status_code == 200, "OAuth login page should return 200"
        assert "Swiggy OAuth 2.0 Authorization" in login_res.text, "Login page should contain Swiggy OAuth title"
        assert "Authorize & Link Zoovy Account" in login_res.text, "Login page should contain submit button"
        console.print(f"  • Browser GET /oauth/login: [green]OK (Status 200, HTML rendered)[/green]")

        # 2. Browser POST /oauth/callback (form submission)
        cb_res = requests.post(f"http://127.0.0.1:{port}/oauth/callback", data={"phone": "9876543210"})
        assert cb_res.status_code == 200, "OAuth callback should return 200"
        assert "Authorization Successful" in cb_res.text, "Callback should return success confirmation"
        console.print(f"  • Browser POST /oauth/callback: [green]OK (Status 200, Session Captured)[/green]")

        assert server.done_event.is_set(), "Server done_event should be triggered"
        assert server.oauth_result is not None, "OAuth result should be populated"
        assert "access_token" in server.oauth_result, "Access token should be present in captured result"
        console.print(f"  • Captured OAuth Token: [cyan]{server.oauth_result['access_token'][:18]}...[/cyan]")
        console.print("  [bold green]✓ Swiggy OAuth 2.0 Browser Server & Callback Flow PASSED[/bold green]\n")
    finally:
        server.shutdown()
        server.server_close()

        # Clean up test files
        if test_json_file.exists():
            test_json_file.unlink()
        if test_oauth_meta_file.exists():
            test_oauth_meta_file.unlink()

        # Restore original user tokens
        for fname, content in token_backups.items():
            try:
                (token_dir / fname).write_text(content, encoding="utf-8")
            except Exception:
                pass

    console.print("[bold cyan]═══════════════════════════════════════════════════════════════[/bold cyan]")
    console.print("[bold green]      ALL SWIGGY & GOAL ENGINE TESTS PASSED (100% SUCCESS)    [/bold green]")
    console.print("[bold cyan]═══════════════════════════════════════════════════════════════[/bold cyan]\n")


if __name__ == "__main__":
    run_tests()
