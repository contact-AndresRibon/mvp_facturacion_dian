from dataclasses import dataclass
from typing import Protocol


@dataclass
class SignResult:
    signed_xml: bytes
    signature_hash: str
    cufe_or_cude: str  # TODO-DIAN: use official CUFE/CUDE formula


class DocumentSigner(Protocol):
    """TODO-DIAN: Implement XAdES-EPES signing with X.509 certificate."""

    def sign(self, xml_bytes: bytes, document_id: str) -> SignResult:
        ...
