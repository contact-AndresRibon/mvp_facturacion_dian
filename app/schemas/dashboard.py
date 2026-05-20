from decimal import Decimal
from typing import Optional
from uuid import UUID

from pydantic import BaseModel


class StatusCount(BaseModel):
    status: str
    count: int


class TopProductItem(BaseModel):
    product_id: Optional[UUID]
    description: str
    quantity_sold: Decimal
    total_sales: Decimal


class DashboardResponse(BaseModel):
    sales_today: Decimal
    sales_month: Decimal
    total_invoices: int
    drafts_count: int
    accepted_count: int
    by_status: list[StatusCount]
    top_products: list[TopProductItem]
