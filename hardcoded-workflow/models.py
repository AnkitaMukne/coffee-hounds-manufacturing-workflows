"""
Pydantic models for NovaBoard Electronics Production Scheduling Agent.
"""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class SalesOrder(BaseModel):
    id: str
    internal_id: str  # e.g. "SO-2024-001"
    customer_name: str
    product_id: str
    product_name: str
    product_code: str  # e.g. "IOT-200" — BOM lookup key
    quantity: int
    deadline: datetime  # parsed from expected_shipping_time
    priority: int = Field(default=3, ge=1, le=5)


class Phase(BaseModel):
    id: str
    name: str
    starts_at: datetime
    ends_at: datetime


class ProductionOrder(BaseModel):
    sales_order: SalesOrder
    starts_at: datetime
    ends_at: datetime
    production_order_id: Optional[str] = None  # set after Arke creation
    phases: list[Phase] = Field(default_factory=list)

    @property
    def on_time(self) -> bool:
        return self.ends_at <= self.sales_order.deadline
