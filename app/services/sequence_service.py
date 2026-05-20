import uuid

from sqlmodel import Session, select

from app.core.config import get_settings
from app.domain.enums import SequenceDocType
from app.models.document_sequence import DocumentSequence
from app.models.tenant import Tenant


class SequenceService:
    @staticmethod
    def _default_prefix(doc_type: SequenceDocType) -> str:
        settings = get_settings()
        if doc_type == SequenceDocType.INVOICE:
            return settings.invoice_prefix
        if doc_type == SequenceDocType.CREDIT_NOTE:
            return settings.credit_note_prefix
        return settings.debit_note_prefix

    @staticmethod
    def resolve_prefix(session: Session, tenant_id: uuid.UUID, doc_type: SequenceDocType) -> str:
        tenant = session.get(Tenant, tenant_id)
        if tenant:
            if doc_type == SequenceDocType.INVOICE and tenant.invoice_prefix:
                return tenant.invoice_prefix
            if doc_type == SequenceDocType.CREDIT_NOTE and tenant.credit_note_prefix:
                return tenant.credit_note_prefix
            if doc_type == SequenceDocType.DEBIT_NOTE and tenant.debit_note_prefix:
                return tenant.debit_note_prefix
        return SequenceService._default_prefix(doc_type)

    @staticmethod
    def next_number(
        session: Session,
        tenant_id: uuid.UUID,
        doc_type: SequenceDocType,
        prefix: str | None = None,
    ) -> tuple[str, str]:
        if prefix is None:
            prefix = SequenceService.resolve_prefix(session, tenant_id, doc_type)

        stmt = (
            select(DocumentSequence)
            .where(DocumentSequence.tenant_id == tenant_id)
            .where(DocumentSequence.doc_type == doc_type)
            .where(DocumentSequence.prefix == prefix)
            .with_for_update()
        )
        seq = session.exec(stmt).first()

        if not seq:
            seq = DocumentSequence(
                tenant_id=tenant_id,
                doc_type=doc_type,
                prefix=prefix,
                last_number=0,
            )
            session.add(seq)
            session.flush()

        seq.last_number += 1
        session.add(seq)
        session.flush()

        number = f"{prefix}-{seq.last_number:06d}"
        return prefix, number
