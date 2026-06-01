import uuid
from datetime import datetime, timezone

from sqlalchemy.exc import OperationalError
from sqlmodel import Session

from app.core.logging import get_logger
from app.db.session import engine
from app.domain.enums import DocumentEventType, DocumentStatus, DocumentType
from app.integrations.dian.mock_adapter import get_dian_gateway
from app.integrations.dian.models import DianMetadata
from app.models.credit_note import CreditNote
from app.models.debit_note import DebitNote
from app.models.document_event import DocumentEvent
from app.models.invoice import Invoice
from app.models.tenant import Tenant
from app.services.events import record_event
from app.storage.local_storage import LocalDocumentStorage
from app.workers.celery_app import celery_app

log = get_logger(__name__)

_TASK_KWARGS = dict(
    bind=True,
    autoretry_for=(ConnectionError, TimeoutError, OperationalError),
    retry_backoff=True,
    retry_backoff_max=300,
    retry_jitter=True,
    max_retries=5,
    acks_late=True,
    time_limit=120,
    soft_time_limit=100,
)


def _is_terminal(status: DocumentStatus) -> bool:
    return status in {DocumentStatus.ACCEPTED, DocumentStatus.REJECTED, DocumentStatus.CANCELLED}


def _record_dian_response_event(
    session: Session,
    *,
    tenant_id: uuid.UUID,
    document_type: DocumentType,
    document_id: uuid.UUID,
    from_status: str,
    to_status: str,
    metadata: dict,
) -> None:
    record_event(
        session,
        tenant_id=tenant_id,
        document_type=document_type,
        document_id=document_id,
        event_type=DocumentEventType.DIAN_RESPONSE,
        from_status=from_status,
        to_status=to_status,
        event_metadata=metadata,
    )


@celery_app.task(name="submit_invoice_to_dian", **_TASK_KWARGS)
def submit_invoice_to_dian(invoice_id: str) -> dict:
    log.info("dian.submit.start", document_type="invoice", document_id=invoice_id)
    with Session(engine) as session:
        invoice = session.get(Invoice, uuid.UUID(invoice_id))
        if not invoice:
            log.warning("dian.submit.not_found", document_type="invoice", document_id=invoice_id)
            return {"error": "invoice not found"}
        if _is_terminal(invoice.status):
            log.info(
                "dian.submit.skipped_terminal",
                document_type="invoice",
                document_id=invoice_id,
                status=invoice.status.value,
            )
            return {"skipped": True, "status": invoice.status.value}
        if invoice.status != DocumentStatus.SUBMITTED:
            log.info(
                "dian.submit.skipped_not_submitted",
                document_type="invoice",
                document_id=invoice_id,
                status=invoice.status.value,
            )
            return {"skipped": True, "status": invoice.status.value}
        if not invoice.xml_path:
            return {"error": "invoice has no xml"}

        tenant = session.get(Tenant, invoice.tenant_id)
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
        _record_dian_response_event(
            session,
            tenant_id=invoice.tenant_id,
            document_type=DocumentType.INVOICE,
            document_id=invoice.id,
            from_status=old_status,
            to_status=to_status,
            metadata=invoice.dian_response,
        )
        session.commit()
        log.info(
            "dian.submit.done",
            document_type="invoice",
            document_id=invoice_id,
            status=to_status,
            track_id=result.track_id,
        )
        return {"invoice_id": invoice_id, "status": to_status, "track_id": result.track_id}


@celery_app.task(name="submit_credit_note_to_dian", **_TASK_KWARGS)
def submit_credit_note_to_dian(credit_note_id: str) -> dict:
    log.info("dian.submit.start", document_type="credit_note", document_id=credit_note_id)
    with Session(engine) as session:
        cn = session.get(CreditNote, uuid.UUID(credit_note_id))
        if not cn:
            log.warning("dian.submit.not_found", document_type="credit_note", document_id=credit_note_id)
            return {"error": "credit note not found"}
        if _is_terminal(cn.status):
            log.info(
                "dian.submit.skipped_terminal",
                document_type="credit_note",
                document_id=credit_note_id,
                status=cn.status.value,
            )
            return {"skipped": True, "status": cn.status.value}
        if cn.status != DocumentStatus.SUBMITTED:
            log.info(
                "dian.submit.skipped_not_submitted",
                document_type="credit_note",
                document_id=credit_note_id,
                status=cn.status.value,
            )
            return {"skipped": True, "status": cn.status.value}
        if not cn.xml_path:
            return {"error": "credit note has no xml"}

        tenant = session.get(Tenant, cn.tenant_id)
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
        _record_dian_response_event(
            session,
            tenant_id=cn.tenant_id,
            document_type=DocumentType.CREDIT_NOTE,
            document_id=cn.id,
            from_status=old_status,
            to_status=to_status,
            metadata=cn.dian_response,
        )
        session.commit()
        log.info(
            "dian.submit.done",
            document_type="credit_note",
            document_id=credit_note_id,
            status=to_status,
            track_id=result.track_id,
        )
        return {"credit_note_id": credit_note_id, "status": to_status, "track_id": result.track_id}


@celery_app.task(name="submit_debit_note_to_dian", **_TASK_KWARGS)
def submit_debit_note_to_dian(debit_note_id: str) -> dict:
    log.info("dian.submit.start", document_type="debit_note", document_id=debit_note_id)
    with Session(engine) as session:
        dn = session.get(DebitNote, uuid.UUID(debit_note_id))
        if not dn:
            log.warning("dian.submit.not_found", document_type="debit_note", document_id=debit_note_id)
            return {"error": "debit note not found"}
        if _is_terminal(dn.status):
            log.info(
                "dian.submit.skipped_terminal",
                document_type="debit_note",
                document_id=debit_note_id,
                status=dn.status.value,
            )
            return {"skipped": True, "status": dn.status.value}
        if dn.status != DocumentStatus.SUBMITTED:
            log.info(
                "dian.submit.skipped_not_submitted",
                document_type="debit_note",
                document_id=debit_note_id,
                status=dn.status.value,
            )
            return {"skipped": True, "status": dn.status.value}
        if not dn.xml_path:
            return {"error": "debit note has no xml"}

        tenant = session.get(Tenant, dn.tenant_id)
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
        _record_dian_response_event(
            session,
            tenant_id=dn.tenant_id,
            document_type=DocumentType.DEBIT_NOTE,
            document_id=dn.id,
            from_status=old_status,
            to_status=to_status,
            metadata=dn.dian_response,
        )
        session.commit()
        log.info(
            "dian.submit.done",
            document_type="debit_note",
            document_id=debit_note_id,
            status=to_status,
            track_id=result.track_id,
        )
        return {"debit_note_id": debit_note_id, "status": to_status, "track_id": result.track_id}
