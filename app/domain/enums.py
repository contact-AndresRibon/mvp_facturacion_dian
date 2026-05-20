from enum import Enum


class UserRole(str, Enum):
    ADMIN = "admin"
    OPERATOR = "operator"


class DocumentStatus(str, Enum):
    DRAFT = "draft"
    SIGNED = "signed"
    SUBMITTED = "submitted"
    ACCEPTED = "accepted"
    REJECTED = "rejected"
    CANCELLED = "cancelled"


class DocumentType(str, Enum):
    INVOICE = "invoice"
    CREDIT_NOTE = "credit_note"
    DEBIT_NOTE = "debit_note"  # prepared for future use


class SequenceDocType(str, Enum):
    INVOICE = "invoice"
    CREDIT_NOTE = "credit_note"
    DEBIT_NOTE = "debit_note"


class PaymentMethod(str, Enum):
    CASH = "cash"
    TRANSFER = "transfer"
    CARD = "card"
    CREDIT = "credit"
    OTHER = "other"


class DocumentEventType(str, Enum):
    CREATED = "created"
    UPDATED = "updated"
    SIGNED = "signed"
    SUBMITTED = "submitted"
    ACCEPTED = "accepted"
    REJECTED = "rejected"
    CANCELLED = "cancelled"
    DIAN_SUBMIT_QUEUED = "dian_submit_queued"
    DIAN_RESPONSE = "dian_response"


class TransitionAction(str, Enum):
    SIGN = "sign"
    SUBMIT = "submit"
    ACCEPT = "accept"
    REJECT = "reject"
    CANCEL = "cancel"
