from datetime import datetime, timezone
from typing import Any
from uuid import UUID

from sqlmodel import Session, select

from app.audit.service import AuditService
from app.core.exceptions import AppError, NotFoundError
from app.domain.enums import (
    DocumentEventType,
    DocumentStatus,
    DocumentType,
    TransitionAction,
)
from app.domain.state_machine import (
    DIAN_SUBMITTABLE_STATUSES,
    event_type_for_transition,
    transition,
)
from app.integrations.signing.mock_signer import get_document_signer
from app.integrations.ubl.builder import (
    build_credit_note_ubl_stub,
    build_debit_note_ubl_stub,
    build_invoice_ubl_stub,
)
from app.models.credit_note import CreditNote, CreditNoteLine
from app.models.debit_note import DebitNote, DebitNoteLine
from app.models.customer import Customer
from app.models.document_event import DocumentEvent
from app.models.invoice import Invoice, InvoiceLine
from app.models.tenant import Tenant
from app.models.user import User
from app.services.events import record_event
from app.storage.local_storage import LocalDocumentStorage
from app.workers.tasks import (
    submit_credit_note_to_dian,
    submit_debit_note_to_dian,
    submit_invoice_to_dian,
)


class DocumentWorkflowService:
    @staticmethod
    def _record_event(
        session: Session,
        *,
        tenant_id: UUID,
        document_type: DocumentType,
        document_id: UUID,
        event_type: DocumentEventType,
        from_status: str | None,
        to_status: str | None,
        user_id: UUID | None,
        event_metadata: dict[str, Any] | None = None,
    ) -> None:
        record_event(
            session,
            tenant_id=tenant_id,
            document_type=document_type,
            document_id=document_id,
            event_type=event_type,
            from_status=from_status,
            to_status=to_status,
            event_metadata=event_metadata,
            user_id=user_id,
        )

    @staticmethod
    def transition_invoice(
        session: Session,
        user: User,
        invoice_id: UUID,
        action: TransitionAction,
        *,
        ip_address: str | None = None,
        request_id: str | None = None,
    ) -> Invoice:
        invoice = session.get(Invoice, invoice_id)
        if not invoice or invoice.tenant_id != user.tenant_id:
            raise NotFoundError("Invoice not found")

        old_status = invoice.status
        new_status = transition(old_status, action)

        if action == TransitionAction.SIGN:
            DocumentWorkflowService._sign_invoice(session, invoice)
        elif action == TransitionAction.SUBMIT:
            invoice.submitted_at = datetime.now(timezone.utc)

        invoice.status = new_status
        invoice.updated_at = datetime.now(timezone.utc)
        session.add(invoice)

        event_type = DocumentEventType(event_type_for_transition(action))
        DocumentWorkflowService._record_event(
            session,
            tenant_id=invoice.tenant_id,
            document_type=DocumentType.INVOICE,
            document_id=invoice.id,
            event_type=event_type,
            from_status=old_status.value,
            to_status=new_status.value,
            user_id=user.id,
        )
        session.commit()
        session.refresh(invoice)

        AuditService.log(
            session,
            tenant_id=user.tenant_id,
            user_id=user.id,
            action=f"INVOICE_{action.value.upper()}",
            resource_type="invoice",
            resource_id=str(invoice.id),
            details={"from": old_status.value, "to": new_status.value},
            ip_address=ip_address,
            request_id=request_id,
        )
        return invoice

    @staticmethod
    def _sign_invoice(session: Session, invoice: Invoice) -> None:
        lines = session.exec(
            select(InvoiceLine).where(InvoiceLine.invoice_id == invoice.id)
        ).all()
        if not lines:
            raise AppError("Invoice must have at least one line", code="no_lines")

        tenant = session.get(Tenant, invoice.tenant_id)
        customer = session.get(Customer, invoice.customer_id)
        if not tenant or not customer:
            raise NotFoundError("Tenant or customer not found")

        line_dicts = [
            {
                "description": l.description,
                "quantity": l.quantity,
                "unit_price": l.unit_price,
                "line_subtotal": l.line_subtotal,
            }
            for l in lines
        ]
        xml = build_invoice_ubl_stub(
            invoice_number=invoice.number,
            issue_date=invoice.issue_date,
            supplier_nit=tenant.nit,
            supplier_name=tenant.legal_name,
            customer_doc=customer.document_number,
            customer_name=customer.name,
            currency=invoice.currency,
            subtotal=invoice.subtotal,
            tax_total=invoice.tax_total,
            total=invoice.total,
            lines=line_dicts,
        )

        signer = get_document_signer()
        sign_result = signer.sign(xml, str(invoice.id))
        storage = LocalDocumentStorage()
        xml_path = storage.save_xml(
            invoice.tenant_id, DocumentType.INVOICE, invoice.id, sign_result.signed_xml
        )
        invoice.xml_path = xml_path
        invoice.cufe = sign_result.cufe_or_cude
        invoice.signed_at = datetime.now(timezone.utc)

    @staticmethod
    def queue_invoice_dian_submit(
        session: Session,
        user: User,
        invoice_id: UUID,
        *,
        ip_address: str | None = None,
        request_id: str | None = None,
    ) -> Invoice:
        invoice = session.get(Invoice, invoice_id)
        if not invoice or invoice.tenant_id != user.tenant_id:
            raise NotFoundError("Invoice not found")
        if invoice.status not in DIAN_SUBMITTABLE_STATUSES:
            raise AppError(
                "Invoice must be signed before DIAN submission",
                code="invalid_status",
            )
        if not invoice.xml_path:
            raise AppError("Invoice has no signed XML", code="no_xml")

        submit_invoice_to_dian.delay(str(invoice.id))
        DocumentWorkflowService._record_event(
            session,
            tenant_id=invoice.tenant_id,
            document_type=DocumentType.INVOICE,
            document_id=invoice.id,
            event_type=DocumentEventType.DIAN_SUBMIT_QUEUED,
            from_status=invoice.status.value,
            to_status=invoice.status.value,
            user_id=user.id,
        )
        session.commit()

        AuditService.log(
            session,
            tenant_id=user.tenant_id,
            user_id=user.id,
            action="INVOICE_DIAN_SUBMIT_QUEUED",
            resource_type="invoice",
            resource_id=str(invoice.id),
            ip_address=ip_address,
            request_id=request_id,
        )
        session.refresh(invoice)
        return invoice

    @staticmethod
    def transition_credit_note(
        session: Session,
        user: User,
        credit_note_id: UUID,
        action: TransitionAction,
        *,
        ip_address: str | None = None,
        request_id: str | None = None,
    ) -> CreditNote:
        cn = session.get(CreditNote, credit_note_id)
        if not cn or cn.tenant_id != user.tenant_id:
            raise NotFoundError("Credit note not found")

        old_status = cn.status
        new_status = transition(old_status, action)

        if action == TransitionAction.SIGN:
            DocumentWorkflowService._sign_credit_note(session, cn)
        elif action == TransitionAction.SUBMIT:
            cn.submitted_at = datetime.now(timezone.utc)

        cn.status = new_status
        cn.updated_at = datetime.now(timezone.utc)
        session.add(cn)

        event_type = DocumentEventType(event_type_for_transition(action))
        DocumentWorkflowService._record_event(
            session,
            tenant_id=cn.tenant_id,
            document_type=DocumentType.CREDIT_NOTE,
            document_id=cn.id,
            event_type=event_type,
            from_status=old_status.value,
            to_status=new_status.value,
            user_id=user.id,
        )
        session.commit()
        session.refresh(cn)

        AuditService.log(
            session,
            tenant_id=user.tenant_id,
            user_id=user.id,
            action=f"CREDIT_NOTE_{action.value.upper()}",
            resource_type="credit_note",
            resource_id=str(cn.id),
            details={"from": old_status.value, "to": new_status.value},
            ip_address=ip_address,
            request_id=request_id,
        )
        return cn

    @staticmethod
    def _sign_credit_note(session: Session, cn: CreditNote) -> None:
        lines = session.exec(
            select(CreditNoteLine).where(CreditNoteLine.credit_note_id == cn.id)
        ).all()
        if not lines:
            raise AppError("Credit note must have lines", code="no_lines")

        tenant = session.get(Tenant, cn.tenant_id)
        customer = session.get(Customer, cn.customer_id)
        invoice = session.get(Invoice, cn.invoice_id)
        if not tenant or not customer or not invoice:
            raise NotFoundError("Related records not found")

        line_dicts = [
            {
                "description": l.description,
                "quantity": l.quantity,
                "line_subtotal": l.line_subtotal,
            }
            for l in lines
        ]
        xml = build_credit_note_ubl_stub(
            credit_note_number=cn.number,
            invoice_number=invoice.number,
            issue_date=cn.issue_date,
            supplier_nit=tenant.nit,
            supplier_name=tenant.legal_name,
            customer_doc=customer.document_number,
            customer_name=customer.name,
            currency=cn.currency,
            subtotal=cn.subtotal,
            tax_total=cn.tax_total,
            total=cn.total,
            reason_code=cn.reason_code,
            lines=line_dicts,
        )

        signer = get_document_signer()
        sign_result = signer.sign(xml, str(cn.id))
        storage = LocalDocumentStorage()
        xml_path = storage.save_xml(
            cn.tenant_id, DocumentType.CREDIT_NOTE, cn.id, sign_result.signed_xml
        )
        cn.xml_path = xml_path
        cn.cude = sign_result.cufe_or_cude
        cn.signed_at = datetime.now(timezone.utc)

    @staticmethod
    def queue_credit_note_dian_submit(
        session: Session,
        user: User,
        credit_note_id: UUID,
        *,
        ip_address: str | None = None,
        request_id: str | None = None,
    ) -> CreditNote:
        cn = session.get(CreditNote, credit_note_id)
        if not cn or cn.tenant_id != user.tenant_id:
            raise NotFoundError("Credit note not found")
        if cn.status not in DIAN_SUBMITTABLE_STATUSES:
            raise AppError("Credit note must be signed", code="invalid_status")
        if not cn.xml_path:
            raise AppError("Credit note has no signed XML", code="no_xml")

        submit_credit_note_to_dian.delay(str(cn.id))
        DocumentWorkflowService._record_event(
            session,
            tenant_id=cn.tenant_id,
            document_type=DocumentType.CREDIT_NOTE,
            document_id=cn.id,
            event_type=DocumentEventType.DIAN_SUBMIT_QUEUED,
            from_status=cn.status.value,
            to_status=cn.status.value,
            user_id=user.id,
        )
        session.commit()

        AuditService.log(
            session,
            tenant_id=user.tenant_id,
            user_id=user.id,
            action="CREDIT_NOTE_DIAN_SUBMIT_QUEUED",
            resource_type="credit_note",
            resource_id=str(cn.id),
            ip_address=ip_address,
            request_id=request_id,
        )
        session.refresh(cn)
        return cn

    @staticmethod
    def transition_debit_note(
        session: Session,
        user: User,
        debit_note_id: UUID,
        action: TransitionAction,
        *,
        ip_address: str | None = None,
        request_id: str | None = None,
    ) -> DebitNote:
        dn = session.get(DebitNote, debit_note_id)
        if not dn or dn.tenant_id != user.tenant_id:
            raise NotFoundError("Debit note not found")

        old_status = dn.status
        new_status = transition(old_status, action)

        if action == TransitionAction.SIGN:
            DocumentWorkflowService._sign_debit_note(session, dn)
        elif action == TransitionAction.SUBMIT:
            dn.submitted_at = datetime.now(timezone.utc)

        dn.status = new_status
        dn.updated_at = datetime.now(timezone.utc)
        session.add(dn)

        event_type = DocumentEventType(event_type_for_transition(action))
        DocumentWorkflowService._record_event(
            session,
            tenant_id=dn.tenant_id,
            document_type=DocumentType.DEBIT_NOTE,
            document_id=dn.id,
            event_type=event_type,
            from_status=old_status.value,
            to_status=new_status.value,
            user_id=user.id,
        )
        session.commit()
        session.refresh(dn)

        AuditService.log(
            session,
            tenant_id=user.tenant_id,
            user_id=user.id,
            action=f"DEBIT_NOTE_{action.value.upper()}",
            resource_type="debit_note",
            resource_id=str(dn.id),
            details={"from": old_status.value, "to": new_status.value},
            ip_address=ip_address,
            request_id=request_id,
        )
        return dn

    @staticmethod
    def _sign_debit_note(session: Session, dn: DebitNote) -> None:
        lines = session.exec(
            select(DebitNoteLine).where(DebitNoteLine.debit_note_id == dn.id)
        ).all()
        if not lines:
            raise AppError("Debit note must have lines", code="no_lines")

        tenant = session.get(Tenant, dn.tenant_id)
        customer = session.get(Customer, dn.customer_id)
        invoice = session.get(Invoice, dn.invoice_id)
        if not tenant or not customer or not invoice:
            raise NotFoundError("Related records not found")

        line_dicts = [
            {
                "description": l.description,
                "quantity": l.quantity,
                "line_subtotal": l.line_subtotal,
            }
            for l in lines
        ]
        xml = build_debit_note_ubl_stub(
            debit_note_number=dn.number,
            invoice_number=invoice.number,
            issue_date=dn.issue_date,
            supplier_nit=tenant.nit,
            supplier_name=tenant.legal_name,
            customer_doc=customer.document_number,
            customer_name=customer.name,
            currency=dn.currency,
            subtotal=dn.subtotal,
            tax_total=dn.tax_total,
            total=dn.total,
            reason_code=dn.reason_code,
            lines=line_dicts,
        )

        signer = get_document_signer()
        sign_result = signer.sign(xml, str(dn.id))
        storage = LocalDocumentStorage()
        xml_path = storage.save_xml(
            dn.tenant_id, DocumentType.DEBIT_NOTE, dn.id, sign_result.signed_xml
        )
        dn.xml_path = xml_path
        dn.cude = sign_result.cufe_or_cude
        dn.signed_at = datetime.now(timezone.utc)

    @staticmethod
    def queue_debit_note_dian_submit(
        session: Session,
        user: User,
        debit_note_id: UUID,
        *,
        ip_address: str | None = None,
        request_id: str | None = None,
    ) -> DebitNote:
        dn = session.get(DebitNote, debit_note_id)
        if not dn or dn.tenant_id != user.tenant_id:
            raise NotFoundError("Debit note not found")
        if dn.status not in DIAN_SUBMITTABLE_STATUSES:
            raise AppError("Debit note must be signed", code="invalid_status")
        if not dn.xml_path:
            raise AppError("Debit note has no signed XML", code="no_xml")

        submit_debit_note_to_dian.delay(str(dn.id))
        DocumentWorkflowService._record_event(
            session,
            tenant_id=dn.tenant_id,
            document_type=DocumentType.DEBIT_NOTE,
            document_id=dn.id,
            event_type=DocumentEventType.DIAN_SUBMIT_QUEUED,
            from_status=dn.status.value,
            to_status=dn.status.value,
            user_id=user.id,
        )
        session.commit()

        AuditService.log(
            session,
            tenant_id=user.tenant_id,
            user_id=user.id,
            action="DEBIT_NOTE_DIAN_SUBMIT_QUEUED",
            resource_type="debit_note",
            resource_id=str(dn.id),
            ip_address=ip_address,
            request_id=request_id,
        )
        session.refresh(dn)
        return dn

    @staticmethod
    def list_events(
        session: Session,
        user: User,
        document_type: DocumentType,
        document_id: UUID,
    ) -> list[DocumentEvent]:
        return list(
            session.exec(
                select(DocumentEvent)
                .where(DocumentEvent.tenant_id == user.tenant_id)
                .where(DocumentEvent.document_type == document_type)
                .where(DocumentEvent.document_id == document_id)
                .order_by(DocumentEvent.created_at)
            ).all()
        )
