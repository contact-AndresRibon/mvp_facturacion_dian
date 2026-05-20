from datetime import date
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Query, Request, status
from fastapi.responses import Response

from app.core.deps import CurrentUserDep, RequestIdDep, SessionDep, get_client_ip
from app.domain.enums import DocumentStatus, DocumentType
from app.schemas.common import MessageResponse, PaginatedResponse
from app.schemas.invoice import (
    DocumentEventResponse,
    InvoiceCreate,
    InvoiceResponse,
    InvoiceUpdate,
    TransitionRequest,
)
from app.services.document_workflow_service import DocumentWorkflowService
from app.services.invoice_service import InvoiceService

router = APIRouter(prefix="/invoices", tags=["invoices"])


@router.get("", response_model=PaginatedResponse[InvoiceResponse])
def list_invoices(
    session: SessionDep,
    user: CurrentUserDep,
    limit: int = 50,
    offset: int = 0,
    status: Optional[DocumentStatus] = None,
    search: Optional[str] = None,
    date_from: Optional[date] = None,
    date_to: Optional[date] = None,
) -> PaginatedResponse[InvoiceResponse]:
    return InvoiceService.list_invoices(
        session,
        user,
        limit=limit,
        offset=offset,
        status=status,
        search=search,
        date_from=date_from,
        date_to=date_to,
    )


@router.post("", response_model=InvoiceResponse, status_code=status.HTTP_201_CREATED)
def create_invoice(
    data: InvoiceCreate,
    session: SessionDep,
    user: CurrentUserDep,
    request: Request,
    request_id: RequestIdDep,
) -> InvoiceResponse:
    return InvoiceService.create(
        session, user, data, ip_address=get_client_ip(request), request_id=request_id
    )


@router.get("/{invoice_id}", response_model=InvoiceResponse)
def get_invoice(
    invoice_id: UUID, session: SessionDep, user: CurrentUserDep
) -> InvoiceResponse:
    return InvoiceService.get(session, user, invoice_id)


@router.patch("/{invoice_id}", response_model=InvoiceResponse)
def update_invoice(
    invoice_id: UUID,
    data: InvoiceUpdate,
    session: SessionDep,
    user: CurrentUserDep,
    request: Request,
    request_id: RequestIdDep,
) -> InvoiceResponse:
    return InvoiceService.update(
        session,
        user,
        invoice_id,
        data,
        ip_address=get_client_ip(request),
        request_id=request_id,
    )


@router.post("/{invoice_id}/transition", response_model=InvoiceResponse)
def transition_invoice(
    invoice_id: UUID,
    data: TransitionRequest,
    session: SessionDep,
    user: CurrentUserDep,
    request: Request,
    request_id: RequestIdDep,
) -> InvoiceResponse:
    invoice = DocumentWorkflowService.transition_invoice(
        session,
        user,
        invoice_id,
        data.action,
        ip_address=get_client_ip(request),
        request_id=request_id,
    )
    return InvoiceService.get(session, user, invoice.id)


@router.post("/{invoice_id}/submit-dian", response_model=MessageResponse)
def submit_invoice_dian(
    invoice_id: UUID,
    session: SessionDep,
    user: CurrentUserDep,
    request: Request,
    request_id: RequestIdDep,
) -> MessageResponse:
    DocumentWorkflowService.queue_invoice_dian_submit(
        session,
        user,
        invoice_id,
        ip_address=get_client_ip(request),
        request_id=request_id,
    )
    return MessageResponse(message="DIAN submission queued")


@router.get("/{invoice_id}/events", response_model=list[DocumentEventResponse])
def list_invoice_events(
    invoice_id: UUID, session: SessionDep, user: CurrentUserDep
) -> list[DocumentEventResponse]:
    InvoiceService.get(session, user, invoice_id)
    events = DocumentWorkflowService.list_events(
        session, user, DocumentType.INVOICE, invoice_id
    )
    return [DocumentEventResponse.model_validate(e) for e in events]


@router.get("/{invoice_id}/pdf")
def download_invoice_pdf(
    invoice_id: UUID, session: SessionDep, user: CurrentUserDep
) -> Response:
    pdf_bytes, number = InvoiceService.get_or_generate_pdf(session, user, invoice_id)
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{number}.pdf"'},
    )
