import hashlib
import uuid

from app.integrations.signing.signer import DocumentSigner, SignResult


class MockSigner(DocumentSigner):
    def sign(self, xml_bytes: bytes, document_id: str) -> SignResult:
        digest = hashlib.sha256(xml_bytes).hexdigest()
        mock_cufe = hashlib.sha384(f"{document_id}:{digest}".encode()).hexdigest()[:96]
        signed = (
            xml_bytes
            + f"\n<!-- MOCK SIGNATURE document_id={document_id} hash={digest[:16]} -->".encode()
        )
        return SignResult(
            signed_xml=signed,
            signature_hash=digest,
            cufe_or_cude=mock_cufe,
        )


def get_document_signer() -> DocumentSigner:
    return MockSigner()
