"""Schémas Pydantic stricts ; les règles métier restent dans domain.py."""
from pydantic import BaseModel, ConfigDict


class Input(BaseModel):
    model_config = ConfigDict(strict=True, extra="forbid")


class ProductCreate(Input):
    name: str
    priceCents: int
    stock: int


class ProductPatch(Input):
    name: str | None = None
    priceCents: int | None = None
    stock: int | None = None


MODELS = (ProductCreate, ProductPatch)