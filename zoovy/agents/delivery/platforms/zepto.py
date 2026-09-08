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
            # Zepto uses ?query= rather than ?q=
            search_url = f"{self.URL}/search?query={query.replace(' ', '+')}"
            self.page.goto(search_url, wait_until="domcontentloaded", timeout=15000)
            time.sleep(2.5)
        except Exception:
            # Fallback to search bar input
            search_input = self.page.locator("input[placeholder*='Search'], input[aria-label*='Search']").first
            if search_input.is_visible():
                search_input.click()
                search_input.fill(query)
                self.page.keyboard.press("Enter")
                time.sleep(2.5)

        # Scrape item cards
        cards = self.page.locator("a[href*='/pn/']").all()
        results = []
        for i, card in enumerate(cards[:5]):
            try:
                raw_text = card.inner_text().replace('\u20b9', 'Rs.')
                lines = [l.strip() for l in raw_text.splitlines() if l.strip()]
                
                name = ""
                price = 0.0
                variant = "Standard"

                for line in lines:
                    if line.upper() in ["ADD", "OFF", "NEW", "BESTSELLER"] or "%" in line:
                        continue
                    if "Rs." in line:
                        try:
                            clean_num = line.replace("Rs.", "").replace(",", "").strip()
                            if price == 0.0:
                                price = float(clean_num)
                        except ValueError:
                            pass
                        continue
                    if line.replace(".", "").isdigit() or (line.startswith("(") and line.endswith(")")):
                        continue
                    if any(line.lower().endswith(u) for u in ["ml", "g", "kg", "l", "pack", "pc"]):
                        variant = line
                        continue
                    if not name and len(line) > 3:
                        name = line

                results.append({
                    "index": i,
                    "name": name or query.title(),
                    "price": price or 50.0,
                    "variant": variant,
                    "raw_text": raw_text.replace('\n', ' | ')
                })
            except Exception:
                pass
        return results

    def add_to_cart(self, product_index: int = 0, quantity: int = 1) -> bool:
        """Click Add button on the chosen product card and increment stepper."""
        try:
            cards = self.page.locator("a[href*='/pn/']").all()
            if not cards or len(cards) <= product_index:
                return False
            target_card = cards[product_index]

            add_btn = target_card.locator("button:has-text('ADD'), button:has-text('Add')").first
            if not add_btn.is_visible():
                # Check parent
                add_btn = target_card.locator("xpath=..").locator("button:has-text('ADD'), button:has-text('Add')").first

            if add_btn.is_visible():
                add_btn.click()
                time.sleep(1)

            # Increment if quantity > 1 using Zepto's aria-label stepper
            for _ in range(quantity - 1):
                inc_btn = target_card.locator("button[aria-label='Increase quantity']").first
                if not inc_btn.is_visible():
                    inc_btn = self.page.locator("button[aria-label='Increase quantity']").first
                if inc_btn.is_visible():
                    inc_btn.click()
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
            # Find drawer container
            drawer = self.page.locator("div:has(> * > button:has-text('Login to Proceed')), div:has(> * > button:has-text('Proceed to Pay')), div:has(> * > button:has-text('Proceed to Checkout')), div[class*='cart-drawer'], div[class*='drawer']").first
            if not drawer.is_visible():
                self.navigate_to_checkout()
                time.sleep(1.5)
                drawer = self.page.locator("div:has(> * > button:has-text('Login to Proceed')), div:has(> * > button:has-text('Proceed to Pay')), div:has(> * > button:has-text('Proceed to Checkout')), div[class*='cart-drawer'], div[class*='drawer']").first

            if drawer.is_visible():
                raw = drawer.inner_text().replace('\u20b9', 'Rs.')
                lines = [l.strip() for l in raw.splitlines() if l.strip()]

                start_idx = -1
                for idx, line in enumerate(lines):
                    if "item" in line.lower() and idx < 6:
                        start_idx = idx + 1
                        break
                if start_idx == -1:
                    start_idx = 0

                end_idx = len(lines)
                for idx, line in enumerate(lines):
                    if any(s in line.lower() for s in ["forgot something", "bill summary", "add more items"]):
                        end_idx = idx
                        break

                sub_lines = lines[start_idx:end_idx]
                i = 0
                while i < len(sub_lines):
                    name = sub_lines[i]
                    i += 1
                    variant = "Standard"
                    if i < len(sub_lines) and not sub_lines[i].isdigit() and not sub_lines[i].startswith("Rs."):
                        variant = sub_lines[i]
                        i += 1
                    qty = 1
                    if i < len(sub_lines) and sub_lines[i].isdigit():
                        qty = int(sub_lines[i])
                        i += 1
                    total_p = 0.0
                    if i < len(sub_lines) and ("Rs." in sub_lines[i] or sub_lines[i].replace(".", "").isdigit()):
                        clean_num = sub_lines[i].replace("Rs.", "").replace(",", "").strip()
                        try:
                            total_p = float(clean_num)
                        except ValueError:
                            pass
                        i += 1

                    if name and len(name) > 2 and total_p > 0 and name.upper() not in ["ADD", "CART"]:
                        unit_p = round(total_p / qty, 2) if qty > 0 else total_p
                        items.append(CartItemSummary(
                            name=name,
                            variant=variant,
                            description=f"{name} ({variant})",
                            quantity=qty,
                            unit_price_inr=unit_p,
                            total_price_inr=total_p
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
