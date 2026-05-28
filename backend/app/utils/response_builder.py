from datetime import datetime, timezone
from math import ceil
from typing import Any, List

from fastapi import Request
from fastapi.encoders import jsonable_encoder

from app.schemas.base_response import ApiErrorResponse, ApiResponse, ErrorDetail, PaginatedData, PaginationMeta


def get_correlation_id(request: Request) -> str:
    return getattr(request.state, "correlation_id", "BACK-UNKNOWN")


def success_response(request: Request, message: str, data: Any = None) -> ApiResponse:
    return ApiResponse(
        success=True,
        message=message,
        data=jsonable_encoder(data),
        correlation_id=get_correlation_id(request),
        timestamp=datetime.now(timezone.utc),
    )


def paginated_response(
    request: Request,
    message: str,
    content: List[Any],
    page: int,
    size: int,
    total_elements: int,
) -> ApiResponse:
    total_pages = ceil(total_elements / size) if size else 0
    return ApiResponse(
        success=True,
        message=message,
        data=PaginatedData(
            content=jsonable_encoder(content),
            pagination=PaginationMeta(
                page=page,
                size=size,
                total_elements=total_elements,
                total_pages=total_pages,
                has_next=page < total_pages,
                has_previous=page > 1,
            ),
        ),
        correlation_id=get_correlation_id(request),
        timestamp=datetime.now(timezone.utc),
    )


def error_response(request: Request, message: str, errors: List[ErrorDetail]) -> ApiErrorResponse:
    return ApiErrorResponse(
        success=False,
        message=message,
        errors=errors,
        correlation_id=get_correlation_id(request),
        timestamp=datetime.now(timezone.utc),
    )
