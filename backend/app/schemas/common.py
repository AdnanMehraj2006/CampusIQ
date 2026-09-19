"""Shared response/envelope schemas."""

from __future__ import annotations

from typing import Any, Generic, List, Optional, TypeVar

from pydantic import BaseModel, ConfigDict

T = TypeVar("T")


class ORMModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)


class PaginationInfo(BaseModel):
    page: int
    page_size: int
    total: int
    total_pages: int


class PaginatedResponse(BaseModel, Generic[T]):
    success: bool = True
    items: List[T]
    pagination: PaginationInfo


class SuccessResponse(BaseModel):
    success: bool = True
    message: str
    data: Optional[Any] = None


class ErrorResponse(BaseModel):
    success: bool = False
    message: str
    error_code: str
    details: Optional[Any] = None


def paginated(items: List[Any], page: int, page_size: int, total: int) -> dict:
    total_pages = (total + page_size - 1) // page_size if page_size else 0
    return {
        "success": True,
        "items": items,
        "pagination": {
            "page": page,
            "page_size": page_size,
            "total": total,
            "total_pages": total_pages,
        },
    }
