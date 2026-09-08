from abc import ABC, abstractmethod
from typing import List, Dict, Any
from playwright.sync_api import Page
from zoovy.core.safety import CartItemSummary


class BasePlatformDriver(ABC):
    def __init__(self, page: Page):
        self.page = page

    @abstractmethod
    def navigate_home(self):
        pass

    @abstractmethod
    def search_product(self, query: str) -> List[Dict[str, Any]]:
        pass

    @abstractmethod
    def add_to_cart(self, product_index: int = 0, quantity: int = 1) -> bool:
        pass

    @abstractmethod
    def inspect_cart(self) -> List[CartItemSummary]:
        pass

    @abstractmethod
    def navigate_to_checkout(self) -> bool:
        pass
