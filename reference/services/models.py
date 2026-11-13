"""Schémas Pydantic stricts ; les règles métier restent dans domain.py."""
from typing import Literal
from pydantic import BaseModel, ConfigDict

class Input(BaseModel):
    model_config = ConfigDict(strict=True, extra="forbid")

class UserCreate(Input):
    name: str
    email: str
    role: Literal["customer", "staff"] = "customer"

class UserPatch(Input):
    name: str | None = None
    email: str | None = None
    role: Literal["customer", "staff"] | None = None

class ProductCreate(Input):
    name: str
    priceCents: int
    stock: int

class ProductPatch(Input):
    name: str | None = None
    priceCents: int | None = None
    stock: int | None = None

class OrderItem(Input):
    productId: int
    quantity: int

class OrderCreate(Input):
    userId: int
    items: list[OrderItem]

class OrderPatch(Input):
    status: Literal["pending", "confirmed", "cancelled"]

MODELS = {"users": (UserCreate, UserPatch), "products": (ProductCreate, ProductPatch),
          "orders": (OrderCreate, OrderPatch)}
