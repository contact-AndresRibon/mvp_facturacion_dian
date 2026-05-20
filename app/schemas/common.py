from typing import Generic, List, TypeVar
from uuid import UUID

from pydantic import BaseModel, ConfigDict

T = TypeVar("T")


class ORMBase(BaseModel):
    model_config = ConfigDict(from_attributes=True)


class PaginatedResponse(BaseModel, Generic[T]):
    items: List[T]
    total: int
    limit: int
    offset: int


class MessageResponse(BaseModel):
    message: str
    detail: str | None = None


class IDResponse(BaseModel):
    id: UUID
