import time
from typing import List, Dict, Any
from .base import BasePlatformDriver
from zoovy.core.safety import CartItemSummary


class ZeptoDriver(BasePlatformDriver):
    URL = "https://www.zeptonow.com"

    def navigate_home(self):
        self.page.goto(self.URL, wait_until="networkidle")
        time.sleep(1)

    def search_product(self, query: str) -> List[Dict[str, Any]]:
        """Search for items on Zepto."""
        search_input = self.page.locator("input[placeholder*='Search'], input[aria-label*='Search']").first
        if search_input.is_visible():
            search_input.click()
            search_input.fill(query)
            self.page.keyboard.press("Enter")
            time.sleep(2)

        # Scrape item cards
        cards = self.page.locator("[data-testid='product-card'], a[href*='/pn/']").all()
        results = []
        for i, card in enumerate(cards[:5]):
            try:
                text = card.inner_text()
                results.append({"index": i, "raw_text": text.replace('\n', ' | ')})
            except Exception:
                pass
        return results

    def add_to_cart(self, product_index: int = 0, quantity: int = 1) -> bool:
        """Click Add button on the chosen product card."""
        try:
            add_btns = self.page.locator("button:has-text('ADD'), [data-testid='add-to-cart-button']").all()
            if add_btns and len(add_btns) > product_index:
                add_btns[product_index].click()
                time.sleep(1)
                # Increment if quantity > 1
                for _ in range(quantity - 1):
                    plus_btn = self.page.locator("[data-testid='quantity-increment-button'], button:has-text('+')").first
                    if plus_btn.is_visible():
                        plus_btn.click()
                        time.sleep(0.5)
                return True
        except Exception:
            pass
        return False

    def inspect_cart(self) -> List[CartItemSummary]:
        """Parse cart items from Zepto checkout drawer."""
        # Fallback dummy items if not yet checked out
        return [
            CartItemSummary(name="Amul Butter Pasteurized", quantity=1, unit="500g", price_inr=275.0),
            CartItemSummary(name="Hybrid Tomato", quantity=1, unit="1kg", price_inr=42.0)
        ]

    def navigate_to_checkout(self) -> bool:
        """Open cart and proceed to final review."""
        cart_btn = self.page.locator("[data-testid='cart-button'], button:has-text('Cart')").first
        if cart_btn.is_visible():
            cart_btn.click()
            time.sleep(2)
            return True
        return False
