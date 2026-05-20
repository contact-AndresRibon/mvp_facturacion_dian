"""siigo features: billing settings, debit notes, invoice payment

Revision ID: 002
Revises: 001
Create Date: 2026-05-19

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "002"
down_revision: Union[str, None] = "001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("tenants", sa.Column("invoice_prefix", sa.String(20), nullable=True))
    op.add_column("tenants", sa.Column("credit_note_prefix", sa.String(20), nullable=True))
    op.add_column("tenants", sa.Column("debit_note_prefix", sa.String(20), nullable=True))
    op.add_column("tenants", sa.Column("resolution_number", sa.String(50), nullable=True))
    op.add_column("tenants", sa.Column("resolution_valid_from", sa.Date(), nullable=True))
    op.add_column("tenants", sa.Column("resolution_valid_to", sa.Date(), nullable=True))

    op.add_column("invoices", sa.Column("due_date", sa.Date(), nullable=True))
    op.add_column(
        "invoices",
        sa.Column("payment_method", sa.String(20), nullable=False, server_default="cash"),
    )

    op.create_table(
        "debit_notes",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("tenant_id", sa.Uuid(), nullable=False),
        sa.Column("customer_id", sa.Uuid(), nullable=False),
        sa.Column("invoice_id", sa.Uuid(), nullable=False),
        sa.Column("number", sa.String(50), nullable=False),
        sa.Column("prefix", sa.String(20), nullable=False),
        sa.Column("status", sa.String(), nullable=False),
        sa.Column("issue_date", sa.Date(), nullable=False),
        sa.Column("reason_code", sa.String(10), nullable=False),
        sa.Column("reason_text", sa.String(500), nullable=True),
        sa.Column("currency", sa.String(3), nullable=False),
        sa.Column("subtotal", sa.Numeric(18, 2), nullable=False),
        sa.Column("tax_total", sa.Numeric(18, 2), nullable=False),
        sa.Column("total", sa.Numeric(18, 2), nullable=False),
        sa.Column("cude", sa.String(255), nullable=True),
        sa.Column("signed_at", sa.DateTime(), nullable=True),
        sa.Column("submitted_at", sa.DateTime(), nullable=True),
        sa.Column("dian_response", sa.JSON(), nullable=True),
        sa.Column("xml_path", sa.String(500), nullable=True),
        sa.Column("pdf_path", sa.String(500), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["customer_id"], ["customers.id"]),
        sa.ForeignKeyConstraint(["invoice_id"], ["invoices.id"]),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("tenant_id", "number", name="uq_debit_note_tenant_number"),
    )
    op.create_index("ix_debit_notes_number", "debit_notes", ["number"])
    op.create_index("ix_debit_notes_status", "debit_notes", ["status"])
    op.create_index("ix_debit_notes_invoice_id", "debit_notes", ["invoice_id"])
    op.create_index("ix_debit_notes_tenant_id", "debit_notes", ["tenant_id"])

    op.create_table(
        "debit_note_lines",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("debit_note_id", sa.Uuid(), nullable=False),
        sa.Column("product_id", sa.Uuid(), nullable=True),
        sa.Column("description", sa.String(500), nullable=False),
        sa.Column("quantity", sa.Numeric(18, 4), nullable=False),
        sa.Column("unit_price", sa.Numeric(18, 2), nullable=False),
        sa.Column("tax_rate", sa.Numeric(5, 2), nullable=False),
        sa.Column("line_subtotal", sa.Numeric(18, 2), nullable=False),
        sa.Column("line_tax", sa.Numeric(18, 2), nullable=False),
        sa.Column("line_total", sa.Numeric(18, 2), nullable=False),
        sa.ForeignKeyConstraint(["debit_note_id"], ["debit_notes.id"]),
        sa.ForeignKeyConstraint(["product_id"], ["products.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_debit_note_lines_debit_note_id", "debit_note_lines", ["debit_note_id"])


def downgrade() -> None:
    op.drop_table("debit_note_lines")
    op.drop_table("debit_notes")
    op.drop_column("invoices", "payment_method")
    op.drop_column("invoices", "due_date")
    op.drop_column("tenants", "resolution_valid_to")
    op.drop_column("tenants", "resolution_valid_from")
    op.drop_column("tenants", "resolution_number")
    op.drop_column("tenants", "debit_note_prefix")
    op.drop_column("tenants", "credit_note_prefix")
    op.drop_column("tenants", "invoice_prefix")
