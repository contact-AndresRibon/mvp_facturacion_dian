from typing import Protocol

from app.integrations.dian.models import DianMetadata, DianStatusResult, DianSubmissionResult


class DianGateway(Protocol):
    """TODO-DIAN: Implement real adapter with WS-Security, certificates, and official endpoints."""

    def submit_document(
        self, xml_bytes: bytes, metadata: DianMetadata
    ) -> DianSubmissionResult:
        ...

    def get_status(self, track_id: str) -> DianStatusResult:
        ...
