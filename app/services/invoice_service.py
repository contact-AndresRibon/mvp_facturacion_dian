from datetime import date
from typing import Optional
from uuid import UUID

from sqlmodel import Session, func, select

from app.audit.service import AuditService
from app.core.exceptions import AppError, NotFoundError
from app.domain.enums import DocumentEventType, DocumentStatus, DocumentType, SequenceDocType
from app.domain.state_machine import EDITABLE_STATUSES
from app.models.customer import Customer
from app.models.document_event import DocumentEvent
from app.models.invoice import Invoice, InvoiceLine
from app.models.tenant import Tenant
from app.models.user import User
from app.pdf.generator import PDFGenerator
from app.schemas.common import PaginatedResponse
from app.schemas.invoice import (
    InvoiceCreate,
    InvoiceLineResponse,
    InvoiceResponse,
    InvoiceUpdate,
)
from app.services.customer_service import CustomerService
from app.services.line_calculator import resolve_line_from_input, sum_lines
from app.services.sequence_service import SequenceService
from app.storage.local_storage import LocalDocumentStorage


class InvoiceService:
    @staticmethod
    def _to_response(session: Session, invoice: Invoice) -> InvoiceResponse:
        lines = session.exec(
            select(InvoiceLine).where(InvoiceLine.invoice_id == invoice.id)
        ).all()
        data = InvoiceResponse.model_validate(invoice)
        data.lines = [InvoiceLineResponse.model_validate(l) for l in lines]
        return data

    @staticmethod
    def list_invoices(
        session: Session,
        user: User,
        *,
        limit: int = 50,
        offset: int = 0,
        status: Optional[DocumentStatus] = None,
        search: Optional[str] = None,
        date_from: Optional[date] = None,
        date_to: Optional[date] = None,
    ) -> PaginatedResponse[InvoiceResponse]:
        base = select(Invoice).where(Invoice.tenant_id == user.tenant_id)
        if status:
            base = base.where(Invoice.status == status)
        if search:
            base = base.where(Invoice.number.ilike(f"%{search}%"))
        if date_from:
            base = base.where(Invoice.issue_date >= date_from)
        if date_to:
            base = base.where(Invoice.issue_date <= date_to)
        total = session.exec(
            select(func.count()).select_from(base.subquery())
        ).one()
        items = session.exec(
            base.order_by(Invoice.created_at.desc()).offset(offset).limit(limit)
        ).all()
        return PaginatedResponse(
            items=[InvoiceService._to_response(session, i) for i in items],
            total=total,
            limit=limit,
            offset=offset,
        )

    @staticmethod
    def create(
        session: Session,
        user: User,
        data: InvoiceCreate,
        *,
        ip_address: str | None = None,
        request_id: str | None = None,
    ) -> InvoiceResponse:
        CustomerService._get_or_404(session, user, data.customer_id)

        prefix, number = SequenceService.next_number(
            session, user.tenant_id, SequenceDocType.INVOICE
        )

        resolved_lines = [
            resolve_line_from_input(session, user.tenant_id, line.model_dump())
            for line in data.lines
        ]
        subtotal, tax_total, total = sum_lines(resolved_lines)

        invoice = Invoice(
            tenant_id=user.tenant_id,
            customer_id=data.customer_id,
            number=number,
            prefix=prefix,
            status=DocumentStatus.DRAFT,
            issue_date=data.issue_date,
            due_date=data.due_date,
            payment_method=data.payment_method,
            currency=data.currency,
            subtotal=subtotal,
            tax_total=tax_total,
            total=total,
            notes=data.notes,
        )
        session.add(invoice)
        session.flush()

        for line in resolved_lines:
            session.add(
                InvoiceLine(
                    invoice_id=invoice.id,
                    product_id=line["product_id"],
                    description=line["description"],
                    quantity=line["quantity"],
                    unit_price=line["unit_price"],
                    tax_rate=line["tax_rate"],
                    line_subtotal=line["line_subtotal"],
                    line_tax=line["line_tax"],
                    line_total=line["line_total"],
                )
            )

        session.add(
            DocumentEvent(
                tenant_id=user.tenant_id,
                document_type=DocumentType.INVOICE,
                document_id=invoice.id,
                event_type=DocumentEventType.CREATED,
                from_status=None,
                to_status=DocumentStatus.DRAFT.value,
                user_id=user.id,
            )
        )
        session.commit()
        session.refresh(invoice)

        AuditService.log(
            session,
            tenant_id=user.tenant_id,
            user_id=user.id,
            action="INVOICE_CREATED",
            resource_type="invoice",
            resource_id=str(invoice.id),
            details={"number": invoice.number},
            ip_address=ip_address,
            request_id=request_id,
        )
        return InvoiceService._to_response(session, invoice)

    @staticmethod
    def get(session: Session, user: User, invoice_id: UUID) -> InvoiceResponse:
        invoice = InvoiceService._get_or_404(session, user, invoice_id)
        return InvoiceService._to_response(session, invoice)

    @staticmethod
    def update(
        session: Session,
        user: User,
        invoice_id: UUID,
        data: InvoiceUpdate,
        *,
        ip_address: str | None = None,
        request_id: str | None = None,
    ) -> InvoiceResponse:
        invoice = InvoiceService._get_or_404(session, user, invoice_id)
        if invoice.status not in EDITABLE_STATUSES:
            raise AppError("Only draft invoices can be edited", code="not_editable")

        if data.customer_id:
            CustomerService._get_or_404(session, user, data.customer_id)
            invoice.customer_id = data.customer_id
        if data.issue_date:
            invoice.issue_date = data.issue_date
        if data.due_date is not None:
            invoice.due_date = data.due_date
        if data.payment_method is not None:
            invoice.payment_method = data.payment_method
        if data.currency is not None:
            invoice.currency = data.currency
        if data.notes is not None:
            invoice.notes = data.notes

        if data.lines is not None:
            existing = session.exec(
                select(InvoiceLine).where(InvoiceLine.invoice_id == invoice.id)
            ).all()
            for line in existing:
                session.delete(line)

            resolved_lines = [
                resolve_line_from_input(session, user.tenant_id, line.model_dump())
                for line in data.lines
            ]
            subtotal, tax_total, total = sum_lines(resolved_lines)
            invoice.subtotal = subtotal
            invoice.tax_total = tax_total
            invoice.total = total

            for line in resolved_lines:
                session.add(
                    InvoiceLine(
                        invoice_id=invoice.id,
                        product_id=line["product_id"],
                        description=line["description"],
                        quantity=line["quantity"],
                        unit_price=line["unit_price"],
                        tax_rate=line["tax_rate"],
                        line_subtotal=line["line_subtotal"],
                        line_tax=line["line_tax"],
                        line_total=line["line_total"],
                    )
                )

        session.add(invoice)
        session.commit()
        session.refresh(invoice)

        AuditService.log(
            session,
            tenant_id=user.tenant_id,
            user_id=user.id,
            action="INVOICE_UPDATED",
            resource_type="invoice",
            resource_id=str(invoice.id),
            ip_address=ip_address,
            request_id=request_id,
        )
        return InvoiceService._to_response(session, invoice)

    @staticmethod
    def get_or_generate_pdf(session: Session, user: User, invoice_id: UUID) -> tuple[bytes, str]:
        invoice = InvoiceService._get_or_404(session, user, invoice_id)
        storage = LocalDocumentStorage()

        if invoice.pdf_path:
            return storage.read_file(invoice.pdf_path), invoice.number

        tenant = session.get(Tenant, invoice.tenant_id)
        customer = session.get(Customer, invoice.customer_id)
        lines = session.exec(
            select(InvoiceLine).where(InvoiceLine.invoice_id == invoice.id)
        ).all()

        line_dicts = [
            {
                "description": l.description,
                "quantity": l.quantity,
                "unit_price": l.unit_price,
                "tax_rate": l.tax_rate,
                "line_total": l.line_total,
            }
            for l in lines
        ]

        pdf_bytes = PDFGenerator.generate_document_pdf(
            doc_type_label="FACTURA ELECTRONICA",
            document_number=invoice.number,
            status=invoice.status,
            issue_date=str(invoice.issue_date),
            tenant_name=tenant.legal_name if tenant else "",
            tenant_nit=tenant.nit if tenant else "",
            customer_name=customer.name if customer else "",
            customer_doc=customer.document_number if customer else "",
            lines=line_dicts,
            subtotal=invoice.subtotal,
            tax_total=invoice.tax_total,
            total=invoice.total,
            notes=invoice.notes,
        )
        path = storage.save_pdf(
            invoice.tenant_id, DocumentType.INVOICE, invoice.id, pdf_bytes
        )
        invoice.pdf_path = path
        session.add(invoice)
        session.commit()
        return pdf_bytes, invoice.number

    @staticmethod
    def _get_or_404(session: Session, user: User, invoice_id: UUID) -> Invoice:
        invoice = session.get(Invoice, invoice_id)
        if not invoice or invoice.tenant_id != user.tenant_id:
            raise NotFoundError("Invoice not found")
        return invoice
