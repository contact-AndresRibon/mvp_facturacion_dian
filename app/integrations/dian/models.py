from dataclasses import dataclass
from typing import Any, Optional


@dataclass
class DianMetadata:
    tenant_nit: str
    document_number: str
    document_type: str  # invoice | credit_note


@dataclass
class DianSubmissionResult:
    success: bool
    track_id: str
    status: str
    message: str
    raw_response: Optional[dict[str, Any]] = None


@dataclass
class DianStatusResult:
    track_id: str
    status: str
    message: str
    raw_response: Optional[dict[str, Any]] = None
