import uuid
from pathlib import Path

from app.core.config import get_settings
from app.domain.enums import DocumentType


class LocalDocumentStorage:
    def __init__(self, base_path: str | None = None) -> None:
        settings = get_settings()
        self.base_path = Path(base_path or settings.storage_path)

    def _tenant_dir(self, tenant_id: uuid.UUID, doc_type: DocumentType) -> Path:
        path = self.base_path / "tenants" / str(tenant_id) / doc_type.value
        path.mkdir(parents=True, exist_ok=True)
        return path

    def save_xml(
        self, tenant_id: uuid.UUID, doc_type: DocumentType, doc_id: uuid.UUID, content: bytes
    ) -> str:
        directory = self._tenant_dir(tenant_id, doc_type)
        file_path = directory / f"{doc_id}.xml"
        file_path.write_bytes(content)
        return str(file_path)

    def save_pdf(
        self, tenant_id: uuid.UUID, doc_type: DocumentType, doc_id: uuid.UUID, content: bytes
    ) -> str:
        directory = self._tenant_dir(tenant_id, doc_type)
        file_path = directory / f"{doc_id}.pdf"
        file_path.write_bytes(content)
        return str(file_path)

    def read_file(self, path: str) -> bytes:
        return Path(path).read_bytes()
