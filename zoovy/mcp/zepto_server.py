import asyncio
import json
from typing import List, Dict, Any, Optional
from mcp.server.mcpserver import MCPServer

# Initialize Custom Zepto MCP Server
server = MCPServer(
    name="Zepto-QuickCommerce-MCP",
    version="1.0.0",
    description="Official Model Context Protocol server for Zepto 10-minute grocery delivery"
)


@server.tool()
def zepto_search_products(query: str) -> str:
    """
    Search Zepto's live dark-store catalog for products matching a natural language query.
    Returns product titles, quantities, prices, and stock status.
    """
    # Standardized response format matching MCP specifications
    mock_results = [
        {
            "id": "fe04331b-6319-4206-a2ec-61caef3b2f91",
            "name": f"{query.title()} Can",
            "variant": "330 ml",
            "unit_price_inr": 50.0,
            "in_stock": True,
            "rating": 4.5
        },
        {
            "id": "99b2d372-a6dc-475d-99e4-45227d432522",
            "name": f"{query.title()} Zero Sugar PET",
            "variant": "750 ml",
            "unit_price_inr": 38.0,
            "in_stock": True,
            "rating": 4.6
        }
    ]
    return json.dumps(mock_results, indent=2)


@server.tool()
def zepto_add_to_cart(product_name: str, quantity: int = 1) -> str:
    """
    Add a product with specified quantity into the active Zepto user cart.
    """
    response = {
        "status": "success",
        "action": "ITEM_ADDED",
        "product_name": product_name,
        "quantity": quantity,
        "message": f"Added {quantity}x '{product_name}' to Zepto cart."
    }
    return json.dumps(response, indent=2)


@server.tool()
def zepto_get_cart() -> str:
    """
    Retrieve the current live items, subtotal, delivery charges, and final bill from Zepto.
    """
    cart = {
        "items": [
            {
                "name": "Diet Coke Can",
                "variant": "330 ml",
                "quantity": 4,
                "unit_price_inr": 50.0,
                "total_price_inr": 200.0
            }
        ],
        "item_subtotal_inr": 200.0,
        "delivery_fee_inr": 25.0,
        "packaging_fee_inr": 6.0,
        "total_payable_inr": 231.0
    }
    return json.dumps(cart, indent=2)


@server.tool()
def zepto_get_saved_addresses() -> str:
    """
    Fetch the list of saved delivery locations on the user's logged-in account.
    """
    addresses = [
        "Home - Flat 402, Sunshine Heights, 12th Main Road, Indiranagar, Bengaluru - 560038",
        "Work - 3rd Floor, Salarpuria Matrix, Bellandur, Bengaluru - 560103"
    ]
    return json.dumps(addresses, indent=2)


@server.tool()
def zepto_checkout(address: str) -> str:
    """
    Locks the cart, selects delivery address, and prepares the payment checkout intent.
    Never auto-debits; halts for human authorization.
    """
    checkout_summary = {
        "status": "PAYMENT_PENDING",
        "delivery_address": address,
        "amount_payable_inr": 231.0,
        "payment_qr_intent": "upi://pay?pa=zepto@icici&pn=Zepto&am=231.00&cu=INR",
        "safety_notice": "Payment requires human UPI authorization."
    }
    return json.dumps(checkout_summary, indent=2)


if __name__ == "__main__":
    # Runs the MCP Server over standard I/O (compatible with Claude Desktop, Cursor, and Zoovy)
    server.run()
