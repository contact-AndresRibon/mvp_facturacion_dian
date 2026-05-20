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
from app.models.customer import Customer
from app.models.debit_note import DebitNote, DebitNoteLine
from app.models.document_event import DocumentEvent
from app.models.invoice import Invoice
from app.models.tenant import Tenant
from app.models.user import User
from app.pdf.generator import PDFGenerator
from app.schemas.common import PaginatedResponse
from app.schemas.debit_note import (
    DebitNoteCreate,
    DebitNoteLineResponse,
    DebitNoteResponse,
)
from app.services.line_calculator import resolve_line_from_input, sum_lines
from app.services.sequence_service import SequenceService
from app.storage.local_storage import LocalDocumentStorage


class DebitNoteService:
    @staticmethod
    def _to_response(session: Session, dn: DebitNote) -> DebitNoteResponse:
        lines = session.exec(
            select(DebitNoteLine).where(DebitNoteLine.debit_note_id == dn.id)
        ).all()
        data = DebitNoteResponse.model_validate(dn)
        data.lines = [DebitNoteLineResponse.model_validate(l) for l in lines]
        return data

    @staticmethod
    def list_debit_notes(
        session: Session, user: User, *, limit: int = 50, offset: int = 0
    ) -> PaginatedResponse[DebitNoteResponse]:
        base = select(DebitNote).where(DebitNote.tenant_id == user.tenant_id)
        total = session.exec(select(func.count()).select_from(base.subquery())).one()
        items = session.exec(
            base.order_by(DebitNote.created_at.desc()).offset(offset).limit(limit)
        ).all()
        return PaginatedResponse(
            items=[DebitNoteService._to_response(session, d) for d in items],
            total=total,
            limit=limit,
            offset=offset,
        )

    @staticmethod
    def create(
        session: Session,
        user: User,
        data: DebitNoteCreate,
        *,
        ip_address: str | None = None,
        request_id: str | None = None,
    ) -> DebitNoteResponse:
        invoice = session.get(Invoice, data.invoice_id)
        if not invoice or invoice.tenant_id != user.tenant_id:
            raise NotFoundError("Invoice not found")
        if invoice.status not in REFERENCE_INVOICE_STATUSES:
            raise AppError(
                "Invoice must be signed, submitted or accepted to create debit note",
                code="invalid_invoice_status",
            )

        customer_id = data.customer_id or invoice.customer_id
        prefix, number = SequenceService.next_number(
            session, user.tenant_id, SequenceDocType.DEBIT_NOTE
        )

        resolved_lines = [
            resolve_line_from_input(session, user.tenant_id, line.model_dump())
            for line in data.lines
        ]
        subtotal, tax_total, total = sum_lines(resolved_lines)

        dn = DebitNote(
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
        session.add(dn)
        session.flush()

        for line in resolved_lines:
            session.add(
                DebitNoteLine(
                    debit_note_id=dn.id,
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
                document_type=DocumentType.DEBIT_NOTE,
                document_id=dn.id,
                event_type=DocumentEventType.CREATED,
                from_status=None,
                to_status=DocumentStatus.DRAFT.value,
                user_id=user.id,
                event_metadata={"invoice_id": str(invoice.id)},
            )
        )
        session.commit()
        session.refresh(dn)

        AuditService.log(
            session,
            tenant_id=user.tenant_id,
            user_id=user.id,
            action="DEBIT_NOTE_CREATED",
            resource_type="debit_note",
            resource_id=str(dn.id),
            details={"number": dn.number, "invoice_id": str(invoice.id)},
            ip_address=ip_address,
            request_id=request_id,
        )
        return DebitNoteService._to_response(session, dn)

    @staticmethod
    def get(session: Session, user: User, debit_note_id: UUID) -> DebitNoteResponse:
        dn = DebitNoteService._get_or_404(session, user, debit_note_id)
        return DebitNoteService._to_response(session, dn)

    @staticmethod
    def _get_or_404(session: Session, user: User, debit_note_id: UUID) -> DebitNote:
        dn = session.get(DebitNote, debit_note_id)
        if not dn or dn.tenant_id != user.tenant_id:
            raise NotFoundError("Debit note not found")
        return dn

    @staticmethod
    def get_or_generate_pdf(
        session: Session, user: User, debit_note_id: UUID
    ) -> tuple[bytes, str]:
        dn = DebitNoteService._get_or_404(session, user, debit_note_id)
        storage = LocalDocumentStorage()
        if dn.pdf_path:
            return storage.read_file(dn.pdf_path), dn.number

        tenant = session.get(Tenant, dn.tenant_id)
        customer = session.get(Customer, dn.customer_id)
        invoice = session.get(Invoice, dn.invoice_id)
        lines = session.exec(
            select(DebitNoteLine).where(DebitNoteLine.debit_note_id == dn.id)
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
            doc_type_label="NOTA DEBITO",
            document_number=dn.number,
            status=dn.status,
            issue_date=str(dn.issue_date),
            tenant_name=tenant.legal_name if tenant else "",
            tenant_nit=tenant.nit if tenant else "",
            customer_name=customer.name if customer else "",
            customer_doc=customer.document_number if customer else "",
            lines=line_dicts,
            subtotal=dn.subtotal,
            tax_total=dn.tax_total,
            total=dn.total,
            notes=dn.reason_text,
            reference=f"Factura {invoice.number}" if invoice else None,
        )
        path = storage.save_pdf(dn.tenant_id, DocumentType.DEBIT_NOTE, dn.id, pdf_bytes)
        dn.pdf_path = path
        session.add(dn)
        session.commit()
        return pdf_bytes, dn.number
