from uuid import UUID

from fastapi import APIRouter, Request, status
from fastapi.responses import Response

from app.core.deps import CurrentUserDep, RequestIdDep, SessionDep, get_client_ip
from app.domain.enums import DocumentType
from app.schemas.common import MessageResponse, PaginatedResponse
from app.schemas.debit_note import DebitNoteCreate, DebitNoteResponse
from app.schemas.invoice import DocumentEventResponse, TransitionRequest
from app.services.debit_note_service import DebitNoteService
from app.services.document_workflow_service import DocumentWorkflowService

router = APIRouter(prefix="/debit-notes", tags=["debit-notes"])


@router.get("", response_model=PaginatedResponse[DebitNoteResponse])
def list_debit_notes(
    session: SessionDep,
    user: CurrentUserDep,
    limit: int = 50,
    offset: int = 0,
) -> PaginatedResponse[DebitNoteResponse]:
    return DebitNoteService.list_debit_notes(session, user, limit=limit, offset=offset)


@router.post("", response_model=DebitNoteResponse, status_code=status.HTTP_201_CREATED)
def create_debit_note(
    data: DebitNoteCreate,
    session: SessionDep,
    user: CurrentUserDep,
    request: Request,
    request_id: RequestIdDep,
) -> DebitNoteResponse:
    return DebitNoteService.create(
        session, user, data, ip_address=get_client_ip(request), request_id=request_id
    )


@router.get("/{debit_note_id}", response_model=DebitNoteResponse)
def get_debit_note(
    debit_note_id: UUID, session: SessionDep, user: CurrentUserDep
) -> DebitNoteResponse:
    return DebitNoteService.get(session, user, debit_note_id)


@router.post("/{debit_note_id}/transition", response_model=DebitNoteResponse)
def transition_debit_note(
    debit_note_id: UUID,
    data: TransitionRequest,
    session: SessionDep,
    user: CurrentUserDep,
    request: Request,
    request_id: RequestIdDep,
) -> DebitNoteResponse:
    dn = DocumentWorkflowService.transition_debit_note(
        session,
        user,
        debit_note_id,
        data.action,
        ip_address=get_client_ip(request),
        request_id=request_id,
    )
    return DebitNoteService.get(session, user, dn.id)


@router.post("/{debit_note_id}/submit-dian", response_model=MessageResponse)
def submit_debit_note_dian(
    debit_note_id: UUID,
    session: SessionDep,
    user: CurrentUserDep,
    request: Request,
    request_id: RequestIdDep,
) -> MessageResponse:
    DocumentWorkflowService.queue_debit_note_dian_submit(
        session,
        user,
        debit_note_id,
        ip_address=get_client_ip(request),
        request_id=request_id,
    )
    return MessageResponse(message="DIAN submission queued")


@router.get("/{debit_note_id}/events", response_model=list[DocumentEventResponse])
def list_debit_note_events(
    debit_note_id: UUID, session: SessionDep, user: CurrentUserDep
) -> list[DocumentEventResponse]:
    DebitNoteService.get(session, user, debit_note_id)
    events = DocumentWorkflowService.list_events(
        session, user, DocumentType.DEBIT_NOTE, debit_note_id
    )
    return [DocumentEventResponse.model_validate(e) for e in events]


@router.get("/{debit_note_id}/pdf")
def download_debit_note_pdf(
    debit_note_id: UUID, session: SessionDep, user: CurrentUserDep
) -> Response:
    pdf_bytes, number = DebitNoteService.get_or_generate_pdf(session, user, debit_note_id)
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{number}.pdf"'},
    )
