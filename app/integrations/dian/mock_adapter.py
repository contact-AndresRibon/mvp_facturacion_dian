import random
import time
import uuid

from app.core.config import get_settings
from app.integrations.dian.gateway import DianGateway
from app.integrations.dian.models import DianMetadata, DianStatusResult, DianSubmissionResult


class MockDianAdapter(DianGateway):
    """Simulates DIAN submission for development and tests."""

    def submit_document(
        self, xml_bytes: bytes, metadata: DianMetadata
    ) -> DianSubmissionResult:
        settings = get_settings()
        time.sleep(0.1)  # simulate network latency
        track_id = str(uuid.uuid4())
        accepted = random.random() < settings.mock_dian_accept_rate
        status = "ACCEPTED" if accepted else "REJECTED"
        return DianSubmissionResult(
            success=accepted,
            track_id=track_id,
            status=status,
            message=f"Mock DIAN response for {metadata.document_number}",
            raw_response={
                "adapter": "mock",
                "track_id": track_id,
                "status": status,
                "xml_size": len(xml_bytes),
            },
        )

    def get_status(self, track_id: str) -> DianStatusResult:
        return DianStatusResult(
            track_id=track_id,
            status="ACCEPTED",
            message="Mock status lookup",
            raw_response={"adapter": "mock"},
        )


def get_dian_gateway() -> DianGateway:
    settings = get_settings()
    if settings.dian_adapter == "mock":
        return MockDianAdapter()
    raise NotImplementedError(
        "Real DIAN adapter not implemented. Set DIAN_ADAPTER=mock. TODO-DIAN."
    )
