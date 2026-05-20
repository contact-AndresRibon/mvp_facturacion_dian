from app.core.exceptions import AppError
from app.domain.enums import DocumentStatus, TransitionAction

# Maps (current_status, action) -> new_status
_TRANSITIONS: dict[tuple[DocumentStatus, TransitionAction], DocumentStatus] = {
    (DocumentStatus.DRAFT, TransitionAction.SIGN): DocumentStatus.SIGNED,
    (DocumentStatus.SIGNED, TransitionAction.SUBMIT): DocumentStatus.SUBMITTED,
    (DocumentStatus.SUBMITTED, TransitionAction.ACCEPT): DocumentStatus.ACCEPTED,
    (DocumentStatus.SUBMITTED, TransitionAction.REJECT): DocumentStatus.REJECTED,
    (DocumentStatus.DRAFT, TransitionAction.CANCEL): DocumentStatus.CANCELLED,
    (DocumentStatus.SIGNED, TransitionAction.CANCEL): DocumentStatus.CANCELLED,
}

# Credit notes can be created against invoices in these states
REFERENCE_INVOICE_STATUSES = {
    DocumentStatus.SIGNED,
    DocumentStatus.SUBMITTED,
    DocumentStatus.ACCEPTED,
}

# Editable only in draft
EDITABLE_STATUSES = {DocumentStatus.DRAFT}

# Can submit to DIAN from signed
DIAN_SUBMITTABLE_STATUSES = {DocumentStatus.SIGNED}


def transition(
    current: DocumentStatus, action: TransitionAction
) -> DocumentStatus:
    key = (current, action)
    if key not in _TRANSITIONS:
        raise AppError(
            f"Transition '{action.value}' not allowed from status '{current.value}'",
            status_code=400,
            code="invalid_transition",
        )
    return _TRANSITIONS[key]


def event_type_for_transition(action: TransitionAction) -> str:
    mapping = {
        TransitionAction.SIGN: "signed",
        TransitionAction.SUBMIT: "submitted",
        TransitionAction.ACCEPT: "accepted",
        TransitionAction.REJECT: "rejected",
        TransitionAction.CANCEL: "cancelled",
    }
    return mapping.get(action.value, action.value)
