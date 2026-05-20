from uuid import UUID

from fastapi import APIRouter, Request, status
from fastapi.responses import Response

from app.core.deps import CurrentUserDep, RequestIdDep, SessionDep, get_client_ip
from app.domain.enums import DocumentType
from app.schemas.common import MessageResponse, PaginatedResponse
from app.schemas.credit_note import CreditNoteCreate, CreditNoteResponse
from app.schemas.invoice import DocumentEventResponse, TransitionRequest
from app.services.credit_note_service import CreditNoteService
from app.services.document_workflow_service import DocumentWorkflowService

router = APIRouter(prefix="/credit-notes", tags=["credit-notes"])


@router.get("", response_model=PaginatedResponse[CreditNoteResponse])
def list_credit_notes(
    session: SessionDep,
    user: CurrentUserDep,
    limit: int = 50,
    offset: int = 0,
) -> PaginatedResponse[CreditNoteResponse]:
    return CreditNoteService.list_credit_notes(session, user, limit=limit, offset=offset)


@router.post("", response_model=CreditNoteResponse, status_code=status.HTTP_201_CREATED)
def create_credit_note(
    data: CreditNoteCreate,
    session: SessionDep,
    user: CurrentUserDep,
    request: Request,
    request_id: RequestIdDep,
) -> CreditNoteResponse:
    return CreditNoteService.create(
        session, user, data, ip_address=get_client_ip(request), request_id=request_id
    )


@router.get("/{credit_note_id}", response_model=CreditNoteResponse)
def get_credit_note(
    credit_note_id: UUID, session: SessionDep, user: CurrentUserDep
) -> CreditNoteResponse:
    return CreditNoteService.get(session, user, credit_note_id)


@router.post("/{credit_note_id}/transition", response_model=CreditNoteResponse)
def transition_credit_note(
    credit_note_id: UUID,
    data: TransitionRequest,
    session: SessionDep,
    user: CurrentUserDep,
    request: Request,
    request_id: RequestIdDep,
) -> CreditNoteResponse:
    cn = DocumentWorkflowService.transition_credit_note(
        session,
        user,
        credit_note_id,
        data.action,
        ip_address=get_client_ip(request),
        request_id=request_id,
    )
    return CreditNoteService.get(session, user, cn.id)


@router.post("/{credit_note_id}/submit-dian", response_model=MessageResponse)
def submit_credit_note_dian(
    credit_note_id: UUID,
    session: SessionDep,
    user: CurrentUserDep,
    request: Request,
    request_id: RequestIdDep,
) -> MessageResponse:
    DocumentWorkflowService.queue_credit_note_dian_submit(
        session,
        user,
        credit_note_id,
        ip_address=get_client_ip(request),
        request_id=request_id,
    )
    return MessageResponse(message="DIAN submission queued")


@router.get("/{credit_note_id}/events", response_model=list[DocumentEventResponse])
def list_credit_note_events(
    credit_note_id: UUID, session: SessionDep, user: CurrentUserDep
) -> list[DocumentEventResponse]:
    CreditNoteService.get(session, user, credit_note_id)
    events = DocumentWorkflowService.list_events(
        session, user, DocumentType.CREDIT_NOTE, credit_note_id
    )
    return [DocumentEventResponse.model_validate(e) for e in events]


@router.get("/{credit_note_id}/pdf")
def download_credit_note_pdf(
    credit_note_id: UUID, session: SessionDep, user: CurrentUserDep
) -> Response:
    pdf_bytes, number = CreditNoteService.get_or_generate_pdf(
        session, user, credit_note_id
    )
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{number}.pdf"'},
    )
