from decimal import Decimal
from typing import Any
from uuid import UUID

from sqlmodel import Session

from app.core.exceptions import NotFoundError
from app.models.product import Product


def calculate_line(
    quantity: Decimal,
    unit_price: Decimal,
    tax_rate: Decimal,
) -> tuple[Decimal, Decimal, Decimal]:
    line_subtotal = (quantity * unit_price).quantize(Decimal("0.01"))
    line_tax = (line_subtotal * tax_rate / Decimal("100")).quantize(Decimal("0.01"))
    line_total = line_subtotal + line_tax
    return line_subtotal, line_tax, line_total


def resolve_line_from_input(
    session: Session,
    tenant_id: UUID,
    line_data: dict[str, Any],
) -> dict[str, Any]:
    quantity = Decimal(str(line_data["quantity"]))
    product_id = line_data.get("product_id")

    if product_id:
        product = session.get(Product, product_id)
        if not product or product.tenant_id != tenant_id or not product.is_active:
            raise NotFoundError("Product not found")
        unit_price = product.unit_price
        tax_rate = product.tax_rate
        description = line_data.get("description") or product.name
        resolved_product_id = product.id
    else:
        if "unit_price" not in line_data:
            raise NotFoundError("unit_price required when product_id is not provided")
        unit_price = Decimal(str(line_data["unit_price"]))
        tax_rate = Decimal(str(line_data.get("tax_rate", "19.00")))
        description = line_data["description"]
        resolved_product_id = None

    line_subtotal, line_tax, line_total = calculate_line(quantity, unit_price, tax_rate)
    return {
        "product_id": resolved_product_id,
        "description": description,
        "quantity": quantity,
        "unit_price": unit_price,
        "tax_rate": tax_rate,
        "line_subtotal": line_subtotal,
        "line_tax": line_tax,
        "line_total": line_total,
    }


def sum_lines(lines: list[dict[str, Any]]) -> tuple[Decimal, Decimal, Decimal]:
    subtotal = sum((l["line_subtotal"] for l in lines), Decimal("0"))
    tax_total = sum((l["line_tax"] for l in lines), Decimal("0"))
    total = sum((l["line_total"] for l in lines), Decimal("0"))
    return subtotal, tax_total, total
