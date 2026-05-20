"""initial schema

Revision ID: 001
Revises:
Create Date: 2026-05-19

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "tenants",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("legal_name", sa.String(255), nullable=False),
        sa.Column("trade_name", sa.String(255), nullable=True),
        sa.Column("nit", sa.String(20), nullable=False),
        sa.Column("dv", sa.String(1), nullable=True),
        sa.Column("email", sa.String(255), nullable=False),
        sa.Column("address", sa.String(500), nullable=True),
        sa.Column("city_code", sa.String(10), nullable=True),
        sa.Column("regime_code", sa.String(10), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_tenants_nit", "tenants", ["nit"])

    op.create_table(
        "users",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("tenant_id", sa.Uuid(), nullable=False),
        sa.Column("email", sa.String(255), nullable=False),
        sa.Column("hashed_password", sa.String(255), nullable=False),
        sa.Column("full_name", sa.String(255), nullable=False),
        sa.Column("role", sa.String(), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_users_email", "users", ["email"])
    op.create_index("ix_users_tenant_id", "users", ["tenant_id"])

    op.create_table(
        "customers",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("tenant_id", sa.Uuid(), nullable=False),
        sa.Column("document_type", sa.String(10), nullable=False),
        sa.Column("document_number", sa.String(50), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("email", sa.String(255), nullable=True),
        sa.Column("address", sa.String(500), nullable=True),
        sa.Column("phone", sa.String(50), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_customers_document_number", "customers", ["document_number"])
    op.create_index("ix_customers_tenant_id", "customers", ["tenant_id"])

    op.create_table(
        "products",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("tenant_id", sa.Uuid(), nullable=False),
        sa.Column("code", sa.String(50), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("description", sa.String(1000), nullable=True),
        sa.Column("unit_price", sa.Numeric(18, 2), nullable=False),
        sa.Column("tax_rate", sa.Numeric(5, 2), nullable=False),
        sa.Column("unit_code", sa.String(10), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_products_code", "products", ["code"])
    op.create_index("ix_products_tenant_id", "products", ["tenant_id"])

    op.create_table(
        "document_sequences",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("tenant_id", sa.Uuid(), nullable=False),
        sa.Column("doc_type", sa.String(), nullable=False),
        sa.Column("prefix", sa.String(20), nullable=False),
        sa.Column("last_number", sa.Integer(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("tenant_id", "doc_type", "prefix", name="uq_sequence_tenant_type_prefix"),
    )
    op.create_index("ix_document_sequences_doc_type", "document_sequences", ["doc_type"])
    op.create_index("ix_document_sequences_tenant_id", "document_sequences", ["tenant_id"])

    op.create_table(
        "invoices",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("tenant_id", sa.Uuid(), nullable=False),
        sa.Column("customer_id", sa.Uuid(), nullable=False),
        sa.Column("number", sa.String(50), nullable=False),
        sa.Column("prefix", sa.String(20), nullable=False),
        sa.Column("status", sa.String(), nullable=False),
        sa.Column("issue_date", sa.Date(), nullable=False),
        sa.Column("currency", sa.String(3), nullable=False),
        sa.Column("subtotal", sa.Numeric(18, 2), nullable=False),
        sa.Column("tax_total", sa.Numeric(18, 2), nullable=False),
        sa.Column("total", sa.Numeric(18, 2), nullable=False),
        sa.Column("notes", sa.String(2000), nullable=True),
        sa.Column("cufe", sa.String(255), nullable=True),
        sa.Column("signed_at", sa.DateTime(), nullable=True),
        sa.Column("submitted_at", sa.DateTime(), nullable=True),
        sa.Column("dian_response", sa.JSON(), nullable=True),
        sa.Column("xml_path", sa.String(500), nullable=True),
        sa.Column("pdf_path", sa.String(500), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["customer_id"], ["customers.id"]),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("tenant_id", "number", name="uq_invoice_tenant_number"),
    )
    op.create_index("ix_invoices_number", "invoices", ["number"])
    op.create_index("ix_invoices_status", "invoices", ["status"])
    op.create_index("ix_invoices_customer_id", "invoices", ["customer_id"])
    op.create_index("ix_invoices_tenant_id", "invoices", ["tenant_id"])

    op.create_table(
        "invoice_lines",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("invoice_id", sa.Uuid(), nullable=False),
        sa.Column("product_id", sa.Uuid(), nullable=True),
        sa.Column("description", sa.String(500), nullable=False),
        sa.Column("quantity", sa.Numeric(18, 4), nullable=False),
        sa.Column("unit_price", sa.Numeric(18, 2), nullable=False),
        sa.Column("tax_rate", sa.Numeric(5, 2), nullable=False),
        sa.Column("line_subtotal", sa.Numeric(18, 2), nullable=False),
        sa.Column("line_tax", sa.Numeric(18, 2), nullable=False),
        sa.Column("line_total", sa.Numeric(18, 2), nullable=False),
        sa.ForeignKeyConstraint(["invoice_id"], ["invoices.id"]),
        sa.ForeignKeyConstraint(["product_id"], ["products.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_invoice_lines_invoice_id", "invoice_lines", ["invoice_id"])

    op.create_table(
        "credit_notes",
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
        sa.UniqueConstraint("tenant_id", "number", name="uq_credit_note_tenant_number"),
    )
    op.create_index("ix_credit_notes_number", "credit_notes", ["number"])
    op.create_index("ix_credit_notes_status", "credit_notes", ["status"])
    op.create_index("ix_credit_notes_invoice_id", "credit_notes", ["invoice_id"])
    op.create_index("ix_credit_notes_tenant_id", "credit_notes", ["tenant_id"])

    op.create_table(
        "credit_note_lines",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("credit_note_id", sa.Uuid(), nullable=False),
        sa.Column("product_id", sa.Uuid(), nullable=True),
        sa.Column("description", sa.String(500), nullable=False),
        sa.Column("quantity", sa.Numeric(18, 4), nullable=False),
        sa.Column("unit_price", sa.Numeric(18, 2), nullable=False),
        sa.Column("tax_rate", sa.Numeric(5, 2), nullable=False),
        sa.Column("line_subtotal", sa.Numeric(18, 2), nullable=False),
        sa.Column("line_tax", sa.Numeric(18, 2), nullable=False),
        sa.Column("line_total", sa.Numeric(18, 2), nullable=False),
        sa.ForeignKeyConstraint(["credit_note_id"], ["credit_notes.id"]),
        sa.ForeignKeyConstraint(["product_id"], ["products.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_credit_note_lines_credit_note_id", "credit_note_lines", ["credit_note_id"])

    op.create_table(
        "document_events",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("tenant_id", sa.Uuid(), nullable=False),
        sa.Column("document_type", sa.String(), nullable=False),
        sa.Column("document_id", sa.Uuid(), nullable=False),
        sa.Column("event_type", sa.String(), nullable=False),
        sa.Column("from_status", sa.String(20), nullable=True),
        sa.Column("to_status", sa.String(20), nullable=True),
        sa.Column("user_id", sa.Uuid(), nullable=True),
        sa.Column("event_metadata", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"]),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_document_events_document_id", "document_events", ["document_id"])
    op.create_index("ix_document_events_document_type", "document_events", ["document_type"])
    op.create_index("ix_document_events_event_type", "document_events", ["event_type"])
    op.create_index("ix_document_events_tenant_id", "document_events", ["tenant_id"])

    op.create_table(
        "audit_logs",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("tenant_id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=True),
        sa.Column("action", sa.String(100), nullable=False),
        sa.Column("resource_type", sa.String(50), nullable=False),
        sa.Column("resource_id", sa.String(50), nullable=True),
        sa.Column("ip_address", sa.String(45), nullable=True),
        sa.Column("request_id", sa.String(50), nullable=True),
        sa.Column("details", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"]),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_audit_logs_action", "audit_logs", ["action"])
    op.create_index("ix_audit_logs_created_at", "audit_logs", ["created_at"])
    op.create_index("ix_audit_logs_request_id", "audit_logs", ["request_id"])
    op.create_index("ix_audit_logs_resource_type", "audit_logs", ["resource_type"])
    op.create_index("ix_audit_logs_tenant_id", "audit_logs", ["tenant_id"])


def downgrade() -> None:
    op.drop_table("audit_logs")
    op.drop_table("document_events")
    op.drop_table("credit_note_lines")
    op.drop_table("credit_notes")
    op.drop_table("invoice_lines")
    op.drop_table("invoices")
    op.drop_table("document_sequences")
    op.drop_table("products")
    op.drop_table("customers")
    op.drop_table("users")
    op.drop_table("tenants")
