from datetime import date
from decimal import Decimal

from sqlmodel import Session, func, select

from app.domain.enums import DocumentStatus
from app.models.invoice import Invoice, InvoiceLine
from app.models.user import User
from app.schemas.dashboard import DashboardResponse, StatusCount, TopProductItem


class DashboardService:
    @staticmethod
    def get_dashboard(session: Session, user: User) -> DashboardResponse:
        tenant_id = user.tenant_id
        today = date.today()
        month_start = today.replace(day=1)

        status_rows = session.exec(
            select(Invoice.status, func.count())
            .where(Invoice.tenant_id == tenant_id)
            .group_by(Invoice.status)
        ).all()
        by_status = [
            StatusCount(status=row[0].value if hasattr(row[0], "value") else str(row[0]), count=row[1])
            for row in status_rows
        ]

        sales_month = session.exec(
            select(func.coalesce(func.sum(Invoice.total), 0))
            .where(Invoice.tenant_id == tenant_id)
            .where(Invoice.status.in_([DocumentStatus.ACCEPTED, DocumentStatus.SIGNED, DocumentStatus.SUBMITTED]))
            .where(Invoice.issue_date >= month_start)
        ).one()

        sales_today = session.exec(
            select(func.coalesce(func.sum(Invoice.total), 0))
            .where(Invoice.tenant_id == tenant_id)
            .where(Invoice.status.in_([DocumentStatus.ACCEPTED, DocumentStatus.SIGNED, DocumentStatus.SUBMITTED]))
            .where(Invoice.issue_date == today)
        ).one()

        total_invoices = session.exec(
            select(func.count()).select_from(Invoice).where(Invoice.tenant_id == tenant_id)
        ).one()

        drafts = next((s.count for s in by_status if s.status == DocumentStatus.DRAFT.value), 0)
        accepted = next((s.count for s in by_status if s.status == DocumentStatus.ACCEPTED.value), 0)

        top_products = DashboardService._top_products(session, tenant_id, limit=4)

        return DashboardResponse(
            sales_today=Decimal(str(sales_today)),
            sales_month=Decimal(str(sales_month)),
            total_invoices=total_invoices,
            drafts_count=drafts,
            accepted_count=accepted,
            by_status=by_status,
            top_products=top_products,
        )

    @staticmethod
    def _top_products(
        session: Session, tenant_id, *, limit: int = 4
    ) -> list[TopProductItem]:
        rows = session.exec(
            select(
                InvoiceLine.product_id,
                InvoiceLine.description,
                func.sum(InvoiceLine.quantity).label("qty"),
                func.sum(InvoiceLine.line_total).label("total"),
            )
            .join(Invoice, Invoice.id == InvoiceLine.invoice_id)
            .where(Invoice.tenant_id == tenant_id)
            .where(
                Invoice.status.in_(
                    [DocumentStatus.ACCEPTED, DocumentStatus.SIGNED, DocumentStatus.SUBMITTED]
                )
            )
            .group_by(InvoiceLine.product_id, InvoiceLine.description)
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
