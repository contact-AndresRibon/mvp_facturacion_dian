from datetime import date
from decimal import Decimal

from pydantic import BaseModel

from app.schemas.dashboard import TopProductItem


class SalesReportResponse(BaseModel):
    date_from: date
    date_to: date
    invoice_count: int
    subtotal_sales: Decimal
    tax_total: Decimal
    total_sales: Decimal


class TopProductsReportResponse(BaseModel):
    date_from: date | None
    date_to: date | None
    items: list[TopProductItem]
