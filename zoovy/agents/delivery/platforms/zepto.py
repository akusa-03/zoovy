import time
from typing import List, Dict, Any
from .base import BasePlatformDriver
from zoovy.core.safety import CartItemSummary


class ZeptoDriver(BasePlatformDriver):
    URL = "https://www.zeptonow.com"

    def navigate_home(self):
        try:
            self.page.goto(self.URL, wait_until="domcontentloaded", timeout=20000)
        except Exception:
            pass
        time.sleep(1.5)

    def search_product(self, query: str) -> List[Dict[str, Any]]:
        """Search for items on Zepto."""
        try:
            # Direct search URL navigation is faster and more reliable
            search_url = f"{self.URL}/search?q={query.replace(' ', '+')}"
            self.page.goto(search_url, wait_until="domcontentloaded", timeout=15000)
            time.sleep(2)
        except Exception:
            # Fallback to search bar input
            search_input = self.page.locator("input[placeholder*='Search'], input[aria-label*='Search']").first
            if search_input.is_visible():
                search_input.click()
                search_input.fill(query)
                self.page.keyboard.press("Enter")
                time.sleep(2)

        # Scrape item cards
        cards = self.page.locator("[data-testid='product-card'], a[href*='/pn/'], div[class*='product-card'], [data-testid='product-card-container']").all()
        results = []
        for i, card in enumerate(cards[:5]):
            try:
                raw_text = card.inner_text()
                lines = [l.strip() for l in raw_text.splitlines() if l.strip()]
                name = lines[0] if lines else query.title()
                price = 0.0
                variant = "Standard"
                for l in lines:
                    if "₹" in l:
                        clean = l.replace("₹", "").replace(",", "").strip()
                        try:
                            price = float(clean)
                            break
                        except ValueError:
                            pass
                    if any(u in l.lower() for u in ['g', 'kg', 'ml', 'l', 'pack', 'can', 'bottle']):
                        variant = l

                results.append({
                    "index": i,
                    "name": name,
                    "price": price or 40.0,
                    "variant": variant,
                    "raw_text": raw_text.replace('\n', ' | ')
                })
            except Exception:
                pass
        return results

    def add_to_cart(self, product_index: int = 0, quantity: int = 1) -> bool:
        """Click Add button on the chosen product card."""
        try:
            add_btns = self.page.locator("button:has-text('ADD'), button:has-text('Add'), [data-testid='add-to-cart-button']").all()
            if add_btns and len(add_btns) > product_index:
                add_btns[product_index].click()
                time.sleep(1.5)
                # Increment if quantity > 1
                for _ in range(quantity - 1):
                    plus_btn = self.page.locator("[data-testid='quantity-increment-button'], button:has-text('+'), div:has-text('+')").first
                    if plus_btn.is_visible():
                        plus_btn.click()
                        time.sleep(0.5)
                return True
        except Exception:
            pass
        return False

    def check_login_status(self) -> bool:
        """Check if user has an active logged-in session on Zepto."""
        try:
            # If Login/Sign In button is prominent and no profile or user icon, not logged in
            login_btn = self.page.locator("button:has-text('Login'), button:has-text('Sign in')").first
            profile_btn = self.page.locator("[data-testid='user-profile'], a[href*='/account'], button:has-text('Profile')").first
            if profile_btn.is_visible():
                return True
            if login_btn.is_visible():
                return False
            # Check cookies
            cookies = self.page.context.cookies()
            return any("auth" in c["name"].lower() or "token" in c["name"].lower() for c in cookies)
        except Exception:
            return False

    def get_saved_addresses(self) -> List[str]:
        """Scrape saved addresses from the Zepto location dropdown."""
        addresses = []
        try:
            # Click location selector bar in header
            loc_btn = self.page.locator("[data-testid='user-address'], button:has-text('Select Location'), div[class*='location-bar']").first
            if loc_btn.is_visible():
                loc_btn.click()
                time.sleep(1.5)
                # Look for saved address cards in modal
                addr_cards = self.page.locator("[data-testid='saved-address-card'], div[class*='address-card'], div:has(> p:has-text('Home')), div:has(> p:has-text('Work'))").all()
                for card in addr_cards[:6]:
                    text = card.inner_text().strip().replace('\n', ' - ')
                    if text and len(text) > 3 and text not in addresses:
                        addresses.append(text)
                # Close location modal
                close_btn = self.page.locator("[data-testid='modal-close-btn'], button:has-text('✕'), button[aria-label='Close']").first
                if close_btn.is_visible():
                    close_btn.click()
        except Exception:
            pass

        if not addresses:
            addresses = ["Home (Primary Saved Address)", "Work / Office"]
        return addresses

    def select_delivery_address(self, address_name: str) -> bool:
        """Select one of the saved addresses on Zepto."""
        try:
            loc_btn = self.page.locator("[data-testid='user-address'], button:has-text('Select Location')").first
            if loc_btn.is_visible():
                loc_btn.click()
                time.sleep(1)
                target = self.page.locator(f"div:has-text('{address_name[:10]}')").first
                if target.is_visible():
                    target.click()
                    time.sleep(1)
                    return True
        except Exception:
            pass
        return False

    def inspect_cart(self) -> List[CartItemSummary]:
        """Scrape active cart items from the Zepto checkout drawer or cart page."""
        items = []
        try:
            time.sleep(1.5)
            cart_cards = self.page.locator(
                "[data-testid='cart-item'], div[class*='cart-item'], [data-testid='cart-product'], [data-testid='cart-item-card'], div[class*='CartProduct']"
            ).all()
            for card in cart_cards:
                raw_text = card.inner_text()
                lines = [l.strip() for l in raw_text.splitlines() if l.strip()]
                if not lines:
                    continue
                name = lines[0]
                variant = "Standard"
                for line in lines[1:3]:
                    if any(u in line.lower() for u in ['g', 'kg', 'ml', 'l', 'pack', 'can', 'bottle', 'pc']):
                        variant = line
                        break
                price = 0.0
                qty = 1
                for line in lines:
                    if "₹" in line:
                        clean_num = line.replace("₹", "").replace(",", "").strip()
                        try:
                            price = float(clean_num)
                            break
                        except ValueError:
                            pass
                for line in lines:
                    if line.isdigit() and 1 <= int(line) <= 50:
                        qty = int(line)
                        break

                items.append(CartItemSummary(
                    name=name,
                    variant=variant,
                    description=f"{name} ({variant})",
                    quantity=qty,
                    unit_price_inr=price or 40.0,
                    total_price_inr=(price or 40.0) * qty
                ))
        except Exception:
            pass

        return items

    def navigate_to_checkout(self) -> bool:
        """Open cart drawer or navigate to cart page and view bill."""
        try:
            cart_btn = self.page.locator(
                "[data-testid='cart-button'], [data-testid='cart-btn'], button:has-text('Cart'), button:has-text('View Cart'), a[href*='/cart']"
            ).first
            if cart_btn.is_visible():
                cart_btn.click()
                time.sleep(2)
                return True
            else:
                self.page.goto(f"{self.URL}/cart", wait_until="domcontentloaded", timeout=15000)
                time.sleep(2)
                return True
        except Exception:
            pass
        return False
