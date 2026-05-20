from sqlmodel import SQLModel

# Import all models so SQLModel.metadata is populated for Alembic
from app.models import (  # noqa: F401
    AuditLog,
    CreditNote,
    CreditNoteLine,
    DebitNote,
    DebitNoteLine,
    Customer,
    DocumentEvent,
    DocumentSequence,
    Invoice,
    InvoiceLine,
    Product,
    Tenant,
    User,
)
