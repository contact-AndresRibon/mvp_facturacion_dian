from uuid import UUID

from sqlmodel import Session, func, select

from app.audit.service import AuditService
from app.core.exceptions import AppError, NotFoundError
from app.domain.enums import (
    DocumentEventType,
    DocumentStatus,
    DocumentType,
    SequenceDocType,
)
from app.domain.state_machine import REFERENCE_INVOICE_STATUSES
from app.models.credit_note import CreditNote, CreditNoteLine
from app.models.customer import Customer
from app.models.document_event import DocumentEvent
from app.models.invoice import Invoice
from app.models.tenant import Tenant
from app.models.user import User
from app.pdf.generator import PDFGenerator
from app.schemas.common import PaginatedResponse
from app.schemas.credit_note import (
    CreditNoteCreate,
    CreditNoteLineResponse,
    CreditNoteResponse,
)
from app.services.invoice_service import InvoiceService
from app.services.line_calculator import resolve_line_from_input, sum_lines
from app.services.sequence_service import SequenceService
from app.storage.local_storage import LocalDocumentStorage


class CreditNoteService:
    @staticmethod
    def _to_response(session: Session, cn: CreditNote) -> CreditNoteResponse:
        lines = session.exec(
            select(CreditNoteLine).where(CreditNoteLine.credit_note_id == cn.id)
        ).all()
        data = CreditNoteResponse.model_validate(cn)
        data.lines = [CreditNoteLineResponse.model_validate(l) for l in lines]
        return data

    @staticmethod
    def list_credit_notes(
        session: Session, user: User, *, limit: int = 50, offset: int = 0
    ) -> PaginatedResponse[CreditNoteResponse]:
        base = select(CreditNote).where(CreditNote.tenant_id == user.tenant_id)
        total = session.exec(
            select(func.count()).select_from(base.subquery())
        ).one()
        items = session.exec(
            base.order_by(CreditNote.created_at.desc()).offset(offset).limit(limit)
        ).all()
        return PaginatedResponse(
            items=[CreditNoteService._to_response(session, c) for c in items],
            total=total,
            limit=limit,
            offset=offset,
        )

    @staticmethod
    def create(
        session: Session,
        user: User,
        data: CreditNoteCreate,
        *,
        ip_address: str | None = None,
        request_id: str | None = None,
    ) -> CreditNoteResponse:
        invoice = session.get(Invoice, data.invoice_id)
        if not invoice or invoice.tenant_id != user.tenant_id:
            raise NotFoundError("Invoice not found")
        if invoice.status not in REFERENCE_INVOICE_STATUSES:
            raise AppError(
                "Invoice must be signed, submitted or accepted to create credit note",
                code="invalid_invoice_status",
            )

        customer_id = data.customer_id or invoice.customer_id

        prefix, number = SequenceService.next_number(
            session, user.tenant_id, SequenceDocType.CREDIT_NOTE
        )

        resolved_lines = [
            resolve_line_from_input(session, user.tenant_id, line.model_dump())
            for line in data.lines
        ]
        subtotal, tax_total, total = sum_lines(resolved_lines)

        cn = CreditNote(
            tenant_id=user.tenant_id,
            customer_id=customer_id,
            invoice_id=invoice.id,
            number=number,
            prefix=prefix,
            status=DocumentStatus.DRAFT,
            issue_date=data.issue_date,
            reason_code=data.reason_code,
            reason_text=data.reason_text,
            subtotal=subtotal,
            tax_total=tax_total,
            total=total,
        )
        session.add(cn)
        session.flush()

        for line in resolved_lines:
            session.add(
                CreditNoteLine(
                    credit_note_id=cn.id,
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
                document_type=DocumentType.CREDIT_NOTE,
                document_id=cn.id,
                event_type=DocumentEventType.CREATED,
                from_status=None,
                to_status=DocumentStatus.DRAFT.value,
                user_id=user.id,
                event_metadata={"invoice_id": str(invoice.id)},
            )
        )
        session.commit()
        session.refresh(cn)

        AuditService.log(
            session,
            tenant_id=user.tenant_id,
            user_id=user.id,
            action="CREDIT_NOTE_CREATED",
            resource_type="credit_note",
            resource_id=str(cn.id),
            details={"number": cn.number, "invoice_id": str(invoice.id)},
            ip_address=ip_address,
            request_id=request_id,
        )
        return CreditNoteService._to_response(session, cn)

    @staticmethod
    def get(session: Session, user: User, credit_note_id: UUID) -> CreditNoteResponse:
        cn = CreditNoteService._get_or_404(session, user, credit_note_id)
        return CreditNoteService._to_response(session, cn)

    @staticmethod
    def get_or_generate_pdf(
        session: Session, user: User, credit_note_id: UUID
    ) -> tuple[bytes, str]:
        cn = CreditNoteService._get_or_404(session, user, credit_note_id)
        storage = LocalDocumentStorage()

        if cn.pdf_path:
            return storage.read_file(cn.pdf_path), cn.number

        tenant = session.get(Tenant, cn.tenant_id)
        customer = session.get(Customer, cn.customer_id)
        invoice = session.get(Invoice, cn.invoice_id)
        lines = session.exec(
            select(CreditNoteLine).where(CreditNoteLine.credit_note_id == cn.id)
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
            doc_type_label="NOTA CREDITO",
            document_number=cn.number,
            status=cn.status,
            issue_date=str(cn.issue_date),
            tenant_name=tenant.legal_name if tenant else "",
            tenant_nit=tenant.nit if tenant else "",
            customer_name=customer.name if customer else "",
            customer_doc=customer.document_number if customer else "",
            lines=line_dicts,
            subtotal=cn.subtotal,
            tax_total=cn.tax_total,
            total=cn.total,
            notes=cn.reason_text,
            reference=f"Factura {invoice.number}" if invoice else None,
        )
        path = storage.save_pdf(
            cn.tenant_id, DocumentType.CREDIT_NOTE, cn.id, pdf_bytes
        )
        cn.pdf_path = path
        session.add(cn)
        session.commit()
        return pdf_bytes, cn.number

    @staticmethod
    def _get_or_404(session: Session, user: User, credit_note_id: UUID) -> CreditNote:
        cn = session.get(CreditNote, credit_note_id)
        if not cn or cn.tenant_id != user.tenant_id:
            raise NotFoundError("Credit note not found")
        return cn
