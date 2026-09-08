from enum import Enum
from typing import List, Optional
from pydantic import BaseModel, Field


class DeliveryPlatform(str, Enum):
    ZEPTO = "zepto"
    SWIGGY = "swiggy"
    ZOMATO = "zomato"


class TargetItem(BaseModel):
    query: str = Field(description="Search phrase for the product")
    quantity: int = Field(default=1, description="Quantity of units required")
    preferred_variant: Optional[str] = Field(default=None, description="Preferred brand or weight, e.g. '500g'")
    max_price_inr: Optional[float] = Field(default=None, description="Maximum budget for this item")


class OrderIntent(BaseModel):
    platform: DeliveryPlatform = Field(description="Target platform: zepto, swiggy, or zomato")
    items: List[TargetItem] = Field(description="List of items to search and add to cart")
    address_preference: Optional[str] = Field(default="Home", description="Preferred delivery address tag")


class ExecutionStep(BaseModel):
    action: str = Field(description="SEARCH, SELECT_PRODUCT, ADD_TO_CART, VIEW_CART, CHECKOUT")
    target: str = Field(description="Selector or search string")
    parameters: dict = Field(default_factory=dict)
