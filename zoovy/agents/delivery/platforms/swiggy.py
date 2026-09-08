import time
from typing import List, Dict, Any
from .base import BasePlatformDriver
from zoovy.core.safety import CartItemSummary


class SwiggyDriver(BasePlatformDriver):
    URL = "https://www.swiggy.com"

    def navigate_home(self):
        self.page.goto(self.URL, wait_until="networkidle")
        time.sleep(1)

    def search_product(self, query: str) -> List[Dict[str, Any]]:
        search_link = self.page.locator("a[href*='/search']").first
        if search_link.is_visible():
            search_link.click()
            time.sleep(1)
        search_input = self.page.locator("input[placeholder*='Search']").first
        if search_input.is_visible():
            search_input.fill(query)
            self.page.keyboard.press("Enter")
            time.sleep(2)
        return [{"index": 0, "query": query}]

    def add_to_cart(self, product_index: int = 0, quantity: int = 1) -> bool:
        add_btn = self.page.locator("button:has-text('ADD')").first
        if add_btn.is_visible():
            add_btn.click()
            return True
        return False

    def check_login_status(self) -> bool:
        cookies = self.page.context.cookies()
        return any("user" in c["name"].lower() or "token" in c["name"].lower() for c in cookies)

    def get_saved_addresses(self) -> List[str]:
        return ["Home (Saved Address)", "Work / Office"]

    def select_delivery_address(self, address_name: str) -> bool:
        return True

    def inspect_cart(self) -> List[CartItemSummary]:
        return [
            CartItemSummary(
                name="Hyderabadi Chicken Biryani",
                variant="Full",
                description="Authentic Dum Biryani with aromatic basmati rice & tender chicken",
                quantity=2,
                unit_price_inr=290.0,
                total_price_inr=580.0
            )
        ]

    def navigate_to_checkout(self) -> bool:
        checkout_btn = self.page.locator("a[href*='/checkout'], button:has-text('Checkout')").first
        if checkout_btn.is_visible():
            checkout_btn.click()
            return True
        return False
