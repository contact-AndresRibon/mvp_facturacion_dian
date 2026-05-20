import uuid
from datetime import datetime, timezone

from sqlmodel import Session, select

from app.domain.enums import DocumentEventType, DocumentStatus, DocumentType
from app.integrations.dian.mock_adapter import get_dian_gateway
from app.integrations.dian.models import DianMetadata
from app.models.credit_note import CreditNote
from app.models.debit_note import DebitNote
from app.models.document_event import DocumentEvent
from app.models.invoice import Invoice
from app.models.tenant import Tenant
from app.storage.local_storage import LocalDocumentStorage
from app.workers.celery_app import celery_app
from app.db.session import engine


def _record_event(
    session: Session,
    *,
    tenant_id: uuid.UUID,
    document_type: DocumentType,
    document_id: uuid.UUID,
    event_type: DocumentEventType,
    from_status: str | None,
    to_status: str | None,
    event_metadata: dict | None = None,
) -> None:
    session.add(
        DocumentEvent(
            tenant_id=tenant_id,
            document_type=document_type,
            document_id=document_id,
            event_type=event_type,
            from_status=from_status,
            to_status=to_status,
            event_metadata=event_metadata,
        )
    )


@celery_app.task(name="submit_invoice_to_dian")
def submit_invoice_to_dian(invoice_id: str) -> dict:
    with Session(engine) as session:
        invoice = session.get(Invoice, uuid.UUID(invoice_id))
        if not invoice:
            return {"error": "invoice not found"}

        tenant = session.get(Tenant, invoice.tenant_id)
        if not invoice.xml_path:
            return {"error": "invoice has no xml"}

        storage = LocalDocumentStorage()
        xml_bytes = storage.read_file(invoice.xml_path)
        gateway = get_dian_gateway()
        result = gateway.submit_document(
            xml_bytes,
            DianMetadata(
                tenant_nit=tenant.nit if tenant else "",
                document_number=invoice.number,
                document_type="invoice",
            ),
        )

        old_status = invoice.status.value
        if result.success:
            invoice.status = DocumentStatus.ACCEPTED
            to_status = DocumentStatus.ACCEPTED.value
        else:
            invoice.status = DocumentStatus.REJECTED
            to_status = DocumentStatus.REJECTED.value

        invoice.submitted_at = datetime.now(timezone.utc)
        invoice.dian_response = result.raw_response or {
            "track_id": result.track_id,
            "status": result.status,
            "message": result.message,
        }
        session.add(invoice)
        _record_event(
            session,
            tenant_id=invoice.tenant_id,
            document_type=DocumentType.INVOICE,
            document_id=invoice.id,
            event_type=DocumentEventType.DIAN_RESPONSE,
            from_status=old_status,
            to_status=to_status,
            event_metadata=invoice.dian_response,
        )
        session.commit()
        return {"invoice_id": invoice_id, "status": to_status, "track_id": result.track_id}


@celery_app.task(name="submit_credit_note_to_dian")
def submit_credit_note_to_dian(credit_note_id: str) -> dict:
    with Session(engine) as session:
        cn = session.get(CreditNote, uuid.UUID(credit_note_id))
        if not cn:
            return {"error": "credit note not found"}

        tenant = session.get(Tenant, cn.tenant_id)
        if not cn.xml_path:
            return {"error": "credit note has no xml"}

        storage = LocalDocumentStorage()
        xml_bytes = storage.read_file(cn.xml_path)
        gateway = get_dian_gateway()
        result = gateway.submit_document(
            xml_bytes,
            DianMetadata(
                tenant_nit=tenant.nit if tenant else "",
                document_number=cn.number,
                document_type="credit_note",
            ),
        )

        old_status = cn.status.value
        if result.success:
            cn.status = DocumentStatus.ACCEPTED
            to_status = DocumentStatus.ACCEPTED.value
        else:
            cn.status = DocumentStatus.REJECTED
            to_status = DocumentStatus.REJECTED.value

        cn.submitted_at = datetime.now(timezone.utc)
        cn.dian_response = result.raw_response or {
            "track_id": result.track_id,
            "status": result.status,
            "message": result.message,
        }
        session.add(cn)
        _record_event(
            session,
            tenant_id=cn.tenant_id,
            document_type=DocumentType.CREDIT_NOTE,
            document_id=cn.id,
            event_type=DocumentEventType.DIAN_RESPONSE,
            from_status=old_status,
            to_status=to_status,
            event_metadata=cn.dian_response,
        )
        session.commit()
        return {"credit_note_id": credit_note_id, "status": to_status, "track_id": result.track_id}


@celery_app.task(name="submit_debit_note_to_dian")
def submit_debit_note_to_dian(debit_note_id: str) -> dict:
    with Session(engine) as session:
        dn = session.get(DebitNote, uuid.UUID(debit_note_id))
        if not dn:
            return {"error": "debit note not found"}

        tenant = session.get(Tenant, dn.tenant_id)
        if not dn.xml_path:
            return {"error": "debit note has no xml"}

        storage = LocalDocumentStorage()
        xml_bytes = storage.read_file(dn.xml_path)
        gateway = get_dian_gateway()
        result = gateway.submit_document(
            xml_bytes,
            DianMetadata(
                tenant_nit=tenant.nit if tenant else "",
                document_number=dn.number,
                document_type="debit_note",
            ),
        )

        old_status = dn.status.value
        if result.success:
            dn.status = DocumentStatus.ACCEPTED
            to_status = DocumentStatus.ACCEPTED.value
        else:
            dn.status = DocumentStatus.REJECTED
            to_status = DocumentStatus.REJECTED.value

        dn.submitted_at = datetime.now(timezone.utc)
        dn.dian_response = result.raw_response or {
            "track_id": result.track_id,
            "status": result.status,
            "message": result.message,
        }
        session.add(dn)
        _record_event(
            session,
            tenant_id=dn.tenant_id,
            document_type=DocumentType.DEBIT_NOTE,
            document_id=dn.id,
            event_type=DocumentEventType.DIAN_RESPONSE,
            from_status=old_status,
            to_status=to_status,
            event_metadata=dn.dian_response,
        )
        session.commit()
        return {"debit_note_id": debit_note_id, "status": to_status, "track_id": result.track_id}
