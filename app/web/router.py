from datetime import date
from decimal import Decimal
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlmodel import select

from app.core.deps import SessionDep
from app.core.security import create_access_token, decode_access_token, verify_password
from app.domain.enums import DocumentStatus, DocumentType, PaymentMethod, TransitionAction
from app.models.customer import Customer
from app.models.invoice import Invoice
from app.models.product import Product
from app.models.user import User
from app.schemas.credit_note import CreditNoteCreate
from app.schemas.customer import CustomerCreate
from app.schemas.debit_note import DebitNoteCreate
from app.schemas.invoice import InvoiceCreate, InvoiceLineInput
from app.schemas.product import ProductCreate
from app.schemas.tenant import TenantUpdate
from app.services.credit_note_service import CreditNoteService
from app.services.customer_service import CustomerService
from app.services.dashboard_service import DashboardService
from app.services.debit_note_service import DebitNoteService
from app.services.document_workflow_service import DocumentWorkflowService
from app.services.invoice_service import InvoiceService
from app.services.product_service import ProductService
from app.services.report_service import ReportService
from app.services.tenant_service import TenantService

templates = Jinja2Templates(directory="app/web/templates")
web_router = APIRouter(include_in_schema=False)


def _get_user_from_cookie(session, request: Request) -> Optional[User]:
    token = request.cookies.get("access_token")
    if not token:
        return None
    try:
        payload = decode_access_token(token)
        user_id = UUID(payload["sub"])
        user = session.get(User, user_id)
        if user and user.is_active:
            return user
    except Exception:
        pass
    return None


@web_router.get("/", response_class=HTMLResponse)
def dashboard(request: Request, session: SessionDep):
    user = _get_user_from_cookie(session, request)
    if not user:
        return RedirectResponse(url="/login", status_code=303)
    dashboard_data = DashboardService.get_dashboard(session, user)
    invoices = session.exec(
        select(Invoice)
        .where(Invoice.tenant_id == user.tenant_id)
        .order_by(Invoice.created_at.desc())
        .limit(10)
    ).all()
    return templates.TemplateResponse(
        request,
        "dashboard.html",
        {"user": user, "dashboard": dashboard_data, "invoices": invoices, "active": "dashboard"},
    )


@web_router.get("/login", response_class=HTMLResponse)
def login_page(request: Request):
    return templates.TemplateResponse(request, "login.html", {})


@web_router.post("/login")
def login_submit(
    request: Request,
    session: SessionDep,
    email: str = Form(...),
    password: str = Form(...),
):
    user = session.exec(select(User).where(User.email == email)).first()
    if not user or not verify_password(password, user.hashed_password):
        return templates.TemplateResponse(
            request,
            "login.html",
            {"error": "Credenciales invalidas"},
            status_code=400,
        )
    token = create_access_token(
        user_id=user.id, tenant_id=user.tenant_id, role=user.role.value
    )
    response = RedirectResponse(url="/", status_code=303)
    response.set_cookie("access_token", token, httponly=True, max_age=86400)
    return response


@web_router.get("/logout")
def logout():
    response = RedirectResponse(url="/login", status_code=303)
    response.delete_cookie("access_token")
    return response


@web_router.get("/customers", response_class=HTMLResponse)
def customers_page(request: Request, session: SessionDep):
    user = _get_user_from_cookie(session, request)
    if not user:
        return RedirectResponse(url="/login", status_code=303)
    result = CustomerService.list_customers(session, user, limit=100)
    return templates.TemplateResponse(
        request,
        "customers.html",
        {"user": user, "customers": result.items, "active": "customers"},
    )


@web_router.get("/customers/new", response_class=HTMLResponse)
def customer_new_page(request: Request, session: SessionDep):
    user = _get_user_from_cookie(session, request)
    if not user:
        return RedirectResponse(url="/login", status_code=303)
    return templates.TemplateResponse(
        request, "customer_form.html", {"user": user, "active": "customers"}
    )


@web_router.post("/customers/new")
def customer_create_submit(
    request: Request,
    session: SessionDep,
    document_type: str = Form(...),
    document_number: str = Form(...),
    name: str = Form(...),
    email: str = Form(""),
):
    user = _get_user_from_cookie(session, request)
    if not user:
        return RedirectResponse(url="/login", status_code=303)
    CustomerService.create(
        session,
        user,
        CustomerCreate(
            document_type=document_type,
            document_number=document_number,
            name=name,
            email=email or None,
        ),
    )
    return RedirectResponse(url="/customers", status_code=303)


@web_router.get("/products", response_class=HTMLResponse)
def products_page(request: Request, session: SessionDep):
    user = _get_user_from_cookie(session, request)
    if not user:
        return RedirectResponse(url="/login", status_code=303)
    result = ProductService.list_products(session, user, limit=100)
    return templates.TemplateResponse(
        request,
        "products.html",
        {"user": user, "products": result.items, "active": "products"},
    )


@web_router.get("/products/new", response_class=HTMLResponse)
def product_new_page(request: Request, session: SessionDep):
    user = _get_user_from_cookie(session, request)
    if not user:
        return RedirectResponse(url="/login", status_code=303)
    return templates.TemplateResponse(
        request, "product_form.html", {"user": user, "active": "products"}
    )


@web_router.post("/products/new")
def product_create_submit(
    request: Request,
    session: SessionDep,
    code: str = Form(...),
    name: str = Form(...),
    unit_price: Decimal = Form(...),
    tax_rate: Decimal = Form(Decimal("19")),
):
    user = _get_user_from_cookie(session, request)
    if not user:
        return RedirectResponse(url="/login", status_code=303)
    ProductService.create(
        session,
        user,
        ProductCreate(code=code, name=name, unit_price=unit_price, tax_rate=tax_rate),
    )
    return RedirectResponse(url="/products", status_code=303)


@web_router.get("/invoices", response_class=HTMLResponse)
def invoices_page(
    request: Request,
    session: SessionDep,
    status: Optional[str] = None,
    search: Optional[str] = None,
):
    user = _get_user_from_cookie(session, request)
    if not user:
        return RedirectResponse(url="/login", status_code=303)
    status_enum = DocumentStatus(status) if status else None
    result = InvoiceService.list_invoices(
        session, user, limit=100, status=status_enum, search=search
    )
    return templates.TemplateResponse(
        request,
        "invoices.html",
        {
            "user": user,
            "invoices": result.items,
            "active": "invoices",
            "filter_status": status,
            "filter_search": search or "",
        },
    )


@web_router.get("/invoices/new", response_class=HTMLResponse)
def invoice_new_page(request: Request, session: SessionDep):
    user = _get_user_from_cookie(session, request)
    if not user:
        return RedirectResponse(url="/login", status_code=303)
    customers = session.exec(
        select(Customer).where(
            Customer.tenant_id == user.tenant_id, Customer.is_active == True
        )
    ).all()
    products = session.exec(
        select(Product).where(
            Product.tenant_id == user.tenant_id, Product.is_active == True
        )
    ).all()
    return templates.TemplateResponse(
        request,
        "invoice_form.html",
        {
            "user": user,
            "customers": customers,
            "products": products,
            "today": date.today(),
            "active": "invoices",
            "payment_methods": list(PaymentMethod),
        },
    )


@web_router.post("/invoices/new")
def invoice_create_submit(
    request: Request,
    session: SessionDep,
    customer_id: UUID = Form(...),
    product_id: UUID = Form(...),
    quantity: Decimal = Form(...),
    issue_date: date = Form(...),
    payment_method: str = Form("cash"),
    currency: str = Form("COP"),
    notes: str = Form(""),
):
    user = _get_user_from_cookie(session, request)
    if not user:
        return RedirectResponse(url="/login", status_code=303)
    data = InvoiceCreate(
        customer_id=customer_id,
        issue_date=issue_date,
        payment_method=PaymentMethod(payment_method),
        currency=currency,
        lines=[InvoiceLineInput(product_id=product_id, quantity=quantity)],
        notes=notes or None,
    )
    invoice = InvoiceService.create(session, user, data)
    return RedirectResponse(url=f"/invoices/{invoice.id}", status_code=303)


@web_router.get("/invoices/{invoice_id}", response_class=HTMLResponse)
def invoice_detail(request: Request, session: SessionDep, invoice_id: UUID):
    user = _get_user_from_cookie(session, request)
    if not user:
        return RedirectResponse(url="/login", status_code=303)
    invoice = InvoiceService.get(session, user, invoice_id)
    events = DocumentWorkflowService.list_events(
        session, user, DocumentType.INVOICE, invoice_id
    )
    return templates.TemplateResponse(
        request,
        "invoice_detail.html",
        {"user": user, "invoice": invoice, "events": events, "active": "invoices"},
    )


@web_router.post("/invoices/{invoice_id}/sign")
def invoice_sign(request: Request, session: SessionDep, invoice_id: UUID):
    user = _get_user_from_cookie(session, request)
    if not user:
        return RedirectResponse(url="/login", status_code=303)
    DocumentWorkflowService.transition_invoice(
        session, user, invoice_id, TransitionAction.SIGN
    )
    return RedirectResponse(url=f"/invoices/{invoice_id}", status_code=303)


@web_router.post("/invoices/{invoice_id}/submit-dian")
def invoice_submit_dian(request: Request, session: SessionDep, invoice_id: UUID):
    user = _get_user_from_cookie(session, request)
    if not user:
        return RedirectResponse(url="/login", status_code=303)
    DocumentWorkflowService.queue_invoice_dian_submit(session, user, invoice_id)
    return RedirectResponse(url=f"/invoices/{invoice_id}", status_code=303)


@web_router.get("/credit-notes", response_class=HTMLResponse)
def credit_notes_page(request: Request, session: SessionDep):
    user = _get_user_from_cookie(session, request)
    if not user:
        return RedirectResponse(url="/login", status_code=303)
    result = CreditNoteService.list_credit_notes(session, user, limit=100)
    return templates.TemplateResponse(
        request,
        "credit_notes.html",
        {"user": user, "credit_notes": result.items, "active": "credit_notes"},
    )


@web_router.get("/credit-notes/new", response_class=HTMLResponse)
def credit_note_new_page(request: Request, session: SessionDep):
    user = _get_user_from_cookie(session, request)
    if not user:
        return RedirectResponse(url="/login", status_code=303)
    invoices = session.exec(
        select(Invoice).where(Invoice.tenant_id == user.tenant_id)
    ).all()
    products = session.exec(
        select(Product).where(
            Product.tenant_id == user.tenant_id, Product.is_active == True
        )
    ).all()
    return templates.TemplateResponse(
        request,
        "credit_note_form.html",
        {
            "user": user,
            "invoices": invoices,
            "products": products,
            "today": date.today(),
            "active": "credit_notes",
        },
    )


@web_router.post("/credit-notes/new")
def credit_note_create_submit(
    request: Request,
    session: SessionDep,
    invoice_id: UUID = Form(...),
    product_id: UUID = Form(...),
    quantity: Decimal = Form(...),
    issue_date: date = Form(...),
    reason_code: str = Form("1"),
    reason_text: str = Form(""),
):
    user = _get_user_from_cookie(session, request)
    if not user:
        return RedirectResponse(url="/login", status_code=303)
    data = CreditNoteCreate(
        invoice_id=invoice_id,
        issue_date=issue_date,
        reason_code=reason_code,
        reason_text=reason_text or None,
        lines=[InvoiceLineInput(product_id=product_id, quantity=quantity)],
    )
    CreditNoteService.create(session, user, data)
    return RedirectResponse(url="/credit-notes", status_code=303)


@web_router.get("/debit-notes", response_class=HTMLResponse)
def debit_notes_page(request: Request, session: SessionDep):
    user = _get_user_from_cookie(session, request)
    if not user:
        return RedirectResponse(url="/login", status_code=303)
    result = DebitNoteService.list_debit_notes(session, user, limit=100)
    return templates.TemplateResponse(
        request,
        "debit_notes.html",
        {"user": user, "debit_notes": result.items, "active": "debit_notes"},
    )


@web_router.get("/debit-notes/new", response_class=HTMLResponse)
def debit_note_new_page(request: Request, session: SessionDep):
    user = _get_user_from_cookie(session, request)
    if not user:
        return RedirectResponse(url="/login", status_code=303)
    invoices = session.exec(
        select(Invoice).where(Invoice.tenant_id == user.tenant_id)
    ).all()
    products = session.exec(
        select(Product).where(
            Product.tenant_id == user.tenant_id, Product.is_active == True
        )
    ).all()
    return templates.TemplateResponse(
        request,
        "debit_note_form.html",
        {
            "user": user,
            "invoices": invoices,
            "products": products,
            "today": date.today(),
            "active": "debit_notes",
        },
    )


@web_router.post("/debit-notes/new")
def debit_note_create_submit(
    request: Request,
    session: SessionDep,
    invoice_id: UUID = Form(...),
    product_id: UUID = Form(...),
    quantity: Decimal = Form(...),
    issue_date: date = Form(...),
    reason_code: str = Form("1"),
    reason_text: str = Form(""),
):
    user = _get_user_from_cookie(session, request)
    if not user:
        return RedirectResponse(url="/login", status_code=303)
    DebitNoteService.create(
        session,
        user,
        DebitNoteCreate(
            invoice_id=invoice_id,
            issue_date=issue_date,
            reason_code=reason_code,
            reason_text=reason_text or None,
            lines=[InvoiceLineInput(product_id=product_id, quantity=quantity)],
        ),
    )
    return RedirectResponse(url="/debit-notes", status_code=303)


@web_router.get("/reports", response_class=HTMLResponse)
def reports_page(request: Request, session: SessionDep):
    user = _get_user_from_cookie(session, request)
    if not user:
        return RedirectResponse(url="/login", status_code=303)
    today = date.today()
    month_start = today.replace(day=1)
    sales = ReportService.sales_report(session, user, date_from=month_start, date_to=today)
    top = ReportService.top_products(session, user, date_from=month_start, date_to=today, limit=10)
    return templates.TemplateResponse(
        request,
        "reports.html",
        {"user": user, "sales": sales, "top_products": top, "active": "reports"},
    )


@web_router.get("/settings/billing", response_class=HTMLResponse)
def billing_settings_page(request: Request, session: SessionDep):
    user = _get_user_from_cookie(session, request)
    if not user:
        return RedirectResponse(url="/login", status_code=303)
    tenant = TenantService.get_my_tenant(session, user)
    return templates.TemplateResponse(
        request, "billing_settings.html", {"user": user, "tenant": tenant, "active": "settings"}
    )


@web_router.post("/settings/billing")
def billing_settings_submit(
    request: Request,
    session: SessionDep,
    invoice_prefix: str = Form(""),
    credit_note_prefix: str = Form(""),
    debit_note_prefix: str = Form(""),
    resolution_number: str = Form(""),
):
    user = _get_user_from_cookie(session, request)
    if not user:
        return RedirectResponse(url="/login", status_code=303)
    TenantService.update_my_tenant(
        session,
        user,
        TenantUpdate(
            invoice_prefix=invoice_prefix or None,
            credit_note_prefix=credit_note_prefix or None,
            debit_note_prefix=debit_note_prefix or None,
            resolution_number=resolution_number or None,
        ),
    )
    return RedirectResponse(url="/settings/billing", status_code=303)
