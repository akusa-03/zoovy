import time
from typing import List, Dict, Any
from .base import BasePlatformDriver
from zoovy.core.safety import CartItemSummary


class ZomatoDriver(BasePlatformDriver):
    URL = "https://www.zomato.com"

    def navigate_home(self):
        self.page.goto(self.URL, wait_until="networkidle")
        time.sleep(1)

    def search_product(self, query: str) -> List[Dict[str, Any]]:
        search_input = self.page.locator("input[placeholder*='Search']").first
        if search_input.is_visible():
            search_input.fill(query)
            self.page.keyboard.press("Enter")
            time.sleep(2)
        return [{"index": 0, "query": query}]

    def add_to_cart(self, product_index: int = 0, quantity: int = 1) -> bool:
        return True

    def inspect_cart(self) -> List[CartItemSummary]:
        return []

    def navigate_to_checkout(self) -> bool:
        return True
