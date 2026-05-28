from datetime import datetime, timezone
from typing import Generic, List, Optional, TypeVar

from pydantic import BaseModel, Field

T = TypeVar("T")


class ErrorDetail(BaseModel):
    field: Optional[str] = None
    code: str
    message: str


class PaginationMeta(BaseModel):
    page: int
    size: int
    total_elements: int
    total_pages: int
    has_next: bool
    has_previous: bool


class PaginatedData(BaseModel, Generic[T]):
    content: List[T]
    pagination: PaginationMeta


class ApiResponse(BaseModel, Generic[T]):
    success: bool = True
    message: str
    data: Optional[T] = None
    correlation_id: str
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class ApiErrorResponse(BaseModel):
    success: bool = False
    message: str
    errors: List[ErrorDetail]
    correlation_id: str
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
