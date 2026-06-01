from fastapi import APIRouter

from app.api.v1.endpoints import (
    audit,
    auth,
    credit_notes,
    customers,
    dashboard,
    debit_notes,
    health,
    invoices,
    products,
    reports,
    tenants,
)

api_router = APIRouter(prefix="/api/v1")
api_router.include_router(health.router)
api_router.include_router(auth.router)
api_router.include_router(tenants.router)
api_router.include_router(customers.router)
api_router.include_router(products.router)
api_router.include_router(invoices.router)
api_router.include_router(credit_notes.router)
api_router.include_router(debit_notes.router)
api_router.include_router(dashboard.router)
api_router.include_router(reports.router)
api_router.include_router(audit.router)
