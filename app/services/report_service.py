from datetime import date
from decimal import Decimal

from sqlmodel import Session, func, select

from app.domain.enums import DocumentStatus
from app.models.invoice import Invoice, InvoiceLine
from app.models.user import User
from app.schemas.dashboard import TopProductItem
from app.schemas.report import SalesReportResponse


class ReportService:
    @staticmethod
    def sales_report(
        session: Session,
        user: User,
        *,
        date_from: date,
        date_to: date,
    ) -> SalesReportResponse:
        tenant_id = user.tenant_id
        statuses = [DocumentStatus.ACCEPTED, DocumentStatus.SIGNED, DocumentStatus.SUBMITTED]

        total = session.exec(
            select(func.coalesce(func.sum(Invoice.total), 0))
            .where(Invoice.tenant_id == tenant_id)
            .where(Invoice.issue_date >= date_from)
            .where(Invoice.issue_date <= date_to)
            .where(Invoice.status.in_(statuses))
        ).one()

        count = session.exec(
            select(func.count())
            .select_from(Invoice)
            .where(Invoice.tenant_id == tenant_id)
            .where(Invoice.issue_date >= date_from)
            .where(Invoice.issue_date <= date_to)
            .where(Invoice.status.in_(statuses))
        ).one()

        tax = session.exec(
            select(func.coalesce(func.sum(Invoice.tax_total), 0))
            .where(Invoice.tenant_id == tenant_id)
            .where(Invoice.issue_date >= date_from)
            .where(Invoice.issue_date <= date_to)
            .where(Invoice.status.in_(statuses))
        ).one()

        return SalesReportResponse(
            date_from=date_from,
            date_to=date_to,
            invoice_count=count,
            subtotal_sales=Decimal(str(total)) - Decimal(str(tax)),
            tax_total=Decimal(str(tax)),
            total_sales=Decimal(str(total)),
        )

    @staticmethod
    def top_products(
        session: Session,
        user: User,
        *,
        date_from: date | None = None,
        date_to: date | None = None,
        limit: int = 10,
    ) -> list[TopProductItem]:
        tenant_id = user.tenant_id
        stmt = (
            select(
                InvoiceLine.product_id,
                InvoiceLine.description,
                func.sum(InvoiceLine.quantity),
                func.sum(InvoiceLine.line_total),
            )
            .join(Invoice, Invoice.id == InvoiceLine.invoice_id)
            .where(Invoice.tenant_id == tenant_id)
            .where(
                Invoice.status.in_(
                    [DocumentStatus.ACCEPTED, DocumentStatus.SIGNED, DocumentStatus.SUBMITTED]
                )
            )
        )
        if date_from:
            stmt = stmt.where(Invoice.issue_date >= date_from)
        if date_to:
            stmt = stmt.where(Invoice.issue_date <= date_to)

        rows = session.exec(
            stmt.group_by(InvoiceLine.product_id, InvoiceLine.description)
            .order_by(func.sum(InvoiceLine.line_total).desc())
            .limit(limit)
        ).all()

        return [
            TopProductItem(
                product_id=row[0],
                description=row[1],
                quantity_sold=Decimal(str(row[2])),
                total_sales=Decimal(str(row[3])),
            )
            for row in rows
        ]
