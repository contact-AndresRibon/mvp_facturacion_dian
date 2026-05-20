"""Seed demo tenant and sample data. Run: python scripts/seed_demo.py"""
import sys
from datetime import date
from decimal import Decimal
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from sqlmodel import Session, select

from app.core.security import get_password_hash
from app.db.session import engine
from app.domain.enums import UserRole
from app.models.customer import Customer
from app.models.product import Product
from app.models.tenant import Tenant
from app.models.user import User
from app.schemas.invoice import InvoiceCreate, InvoiceLineInput
from app.services.invoice_service import InvoiceService


def main() -> None:
    with Session(engine) as session:
        existing = session.exec(
            select(User).where(User.email == "admin@demo.com")
        ).first()
        if existing:
            print("Demo data already exists. admin@demo.com")
            return

        tenant = Tenant(
            legal_name="Empresa Demo SAS",
            trade_name="Demo",
            nit="900123456",
            dv="1",
            email="contacto@demo.com",
            address="Calle 123, Bogota",
        )
        session.add(tenant)
        session.flush()

        user = User(
            tenant_id=tenant.id,
            email="admin@demo.com",
            hashed_password=get_password_hash("demo1234"),
            full_name="Administrador Demo",
            role=UserRole.ADMIN,
        )
        session.add(user)
        session.flush()

        customer = Customer(
            tenant_id=tenant.id,
            document_type="NIT",
            document_number="800987654",
            name="Cliente Ejemplo SAS",
            email="cliente@ejemplo.com",
        )
        product = Product(
            tenant_id=tenant.id,
            code="CONS-001",
            name="Servicio de consultoria",
            unit_price=Decimal("150000.00"),
            tax_rate=Decimal("19.00"),
        )
        session.add(customer)
        session.add(product)
        session.commit()
        session.refresh(user)
        session.refresh(customer)
        session.refresh(product)

        invoice = InvoiceService.create(
            session,
            user,
            InvoiceCreate(
                customer_id=customer.id,
                issue_date=date.today(),
                lines=[InvoiceLineInput(product_id=product.id, quantity=Decimal("1"))],
                notes="Factura de demostracion",
            ),
        )
        print("Seed completed.")
        print("  Login: admin@demo.com / demo1234")
        print(f"  Invoice created: {invoice.number} ({invoice.status})")


if __name__ == "__main__":
    main()
