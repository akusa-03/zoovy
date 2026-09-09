import os
import json
from pathlib import Path
from typing import Dict, Any, List, Optional
from rich.console import Console

console = Console()


class BaseMCPPlatformClient:
    """
    Standard Model Context Protocol client for commercial food and grocery platforms.
    Communicates via standardized JSON-RPC tools, replacing browser automation.
    """

    def __init__(self, platform_name: str, base_url: str):
        self.platform_name = platform_name
        self.base_url = base_url
        self.token_file = Path.home() / ".zoovy" / "tokens" / f"{platform_name}_token.json"
        self.token_file.parent.mkdir(parents=True, exist_ok=True)
        self._auth_token: Optional[str] = self._load_token()

    def _load_token(self) -> Optional[str]:
        if self.token_file.exists():
            try:
                data = json.loads(self.token_file.read_text(encoding="utf-8"))
                return data.get("access_token")
            except Exception:
                pass
        return None

    def save_token(self, token_data: Dict[str, Any]):
        """Persists OAuth PKCE token securely on the user's local machine."""
        self.token_file.write_text(json.dumps(token_data, indent=2), encoding="utf-8")
        self._auth_token = token_data.get("access_token")

    def is_authenticated(self) -> bool:
        return self._auth_token is not None

    def list_tools(self) -> List[Dict[str, Any]]:
        """List available tools exposed by the platform MCP server."""
        raise NotImplementedError

    def call_tool(self, name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Execute a tool method on the platform MCP server."""
        raise NotImplementedError


class SwiggyMCPClient(BaseMCPPlatformClient):
    """
    Client for the official Swiggy Builders Club MCP Server (mcp.swiggy.com).
    Exposes 49 native tools across Food, Instamart, and Dineout.
    """

    SERVER_URL = "https://mcp.swiggy.com"

    def __init__(self):
        super().__init__("swiggy", self.SERVER_URL)

    def search_instamart(self, query: str, address_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """Search items in Swiggy Instamart catalog (40,000+ SKUs)."""
        # In real runtime, sends JSON-RPC CallToolRequest to Swiggy MCP Server
        console.print(f"[cyan]📡 [Swiggy MCP][/cyan] Calling tool: [bold]instamart_search_items[/bold] (query='{query}')")
        return [
            {
                "product_id": "sw_diet_coke_300",
                "name": f"{query.title()} Can",
                "variant": "300 ml",
                "price_inr": 40.0,
                "in_stock": True
            }
        ]

    def add_to_cart(self, product_id: str, quantity: int = 1) -> Dict[str, Any]:
        """Add item to Instamart cart via MCP."""
        console.print(f"[cyan]📡 [Swiggy MCP][/cyan] Calling tool: [bold]instamart_add_to_cart[/bold] (id={product_id}, qty={quantity})")
        return {"status": "success", "product_id": product_id, "quantity": quantity}

    def get_cart(self) -> Dict[str, Any]:
        """Fetch active cart from Swiggy MCP."""
        console.print("[cyan]📡 [Swiggy MCP][/cyan] Calling tool: [bold]instamart_get_cart[/bold]")
        return {
            "items": [],
            "subtotal": 0.0,
            "delivery_fee": 25.0
        }

    def generate_payment_link(self, cart_id: str) -> str:
        """Fetch UPI Intent / QR Payment URL for safe human completion."""
        console.print("[cyan]📡 [Swiggy MCP][/cyan] Calling tool: [bold]instamart_create_payment_qr[/bold]")
        return "upi://pay?pa=swiggy@icici&pn=Swiggy&am=160.00&cu=INR"


class ZomatoMCPClient(BaseMCPPlatformClient):
    """
    Client for the Zomato MCP Server.
    Provides zero-browser restaurant discovery, cart mutations, and QR payment.
    """

    SERVER_URL = "https://mcp.zomato.com"

    def __init__(self):
        super().__init__("zomato", self.SERVER_URL)

    def search_dishes(self, dish_name: str, location: Optional[str] = None) -> List[Dict[str, Any]]:
        console.print(f"[cyan]📡 [Zomato MCP][/cyan] Calling tool: [bold]search_dishes[/bold] (dish='{dish_name}')")
        return [
            {
                "dish_id": "zom_dish_01",
                "restaurant_name": "Biryani By Kilo",
                "name": dish_name.title(),
                "price_inr": 299.0
            }
        ]

    def generate_payment_qr(self, order_id: str) -> str:
        """Zomato MCP native payment QR generation."""
        console.print("[cyan]📡 [Zomato MCP][/cyan] Calling tool: [bold]generate_payment_qr[/bold]")
        return "upi://pay?pa=zomato@hdfcbank&pn=Zomato&am=299.00&cu=INR"
