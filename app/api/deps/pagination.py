"""Pagination dependencies for FastAPI."""

from typing import Generic, TypeVar

from fastapi import Query
from pydantic import BaseModel, Field

T = TypeVar("T")

DEFAULT_PAGE_SIZE = 20
MAX_PAGE_SIZE = 100


class PaginationParams:
    """Pagination parameters for list endpoints."""

    def __init__(
        self,
        page: int = Query(1, ge=1, description="Page number (1-indexed)"),
        page_size: int = Query(
            DEFAULT_PAGE_SIZE,
            ge=1,
            le=MAX_PAGE_SIZE,
            description=f"Items per page (max {MAX_PAGE_SIZE})",
        ),
        sort_by: str | None = Query(None, description="Field to sort by"),
        sort_order: str = Query(
            "desc",
            pattern="^(asc|desc)$",
            description="Sort order (asc or desc)",
        ),
    ):
        self.page = page
        self.page_size = page_size
        self.sort_by = sort_by
        self.sort_order = sort_order

    @property
    def offset(self) -> int:
        """Calculate database offset."""
        return (self.page - 1) * self.page_size

    @property
    def limit(self) -> int:
        """Get limit for query."""
        return self.page_size


def get_pagination(
    page: int = Query(1, ge=1, description="Page number (1-indexed)"),
    page_size: int = Query(
        DEFAULT_PAGE_SIZE,
        ge=1,
        le=MAX_PAGE_SIZE,
        description=f"Items per page (max {MAX_PAGE_SIZE})",
    ),
    sort_by: str | None = Query(None, description="Field to sort by"),
    sort_order: str = Query(
        "desc",
        pattern="^(asc|desc)$",
        description="Sort order (asc or desc)",
    ),
) -> PaginationParams:
    """Dependency for pagination parameters."""
    return PaginationParams(
        page=page,
        page_size=page_size,
        sort_by=sort_by,
        sort_order=sort_order,
    )


class PaginatedResponse(BaseModel, Generic[T]):
    """Standard paginated response format."""

    items: list[T] = Field(description="List of items for current page")
    total: int = Field(description="Total number of items")
    page: int = Field(description="Current page number")
    page_size: int = Field(description="Items per page")
    pages: int = Field(description="Total number of pages")
    has_next: bool = Field(description="Whether there is a next page")
    has_prev: bool = Field(description="Whether there is a previous page")

    @classmethod
    def create(
        cls,
        items: list[T],
        total: int,
        pagination: PaginationParams,
    ) -> "PaginatedResponse[T]":
        """Create paginated response from items and pagination params."""
        pages = (
            (total + pagination.page_size - 1) // pagination.page_size
            if total > 0
            else 1
        )
        return cls(
            items=items,
            total=total,
            page=pagination.page,
            page_size=pagination.page_size,
            pages=pages,
            has_next=pagination.page < pages,
            has_prev=pagination.page > 1,
        )


class CursorPaginationParams:
    """Cursor-based pagination parameters for efficient deep pagination."""

    def __init__(
        self,
        cursor: str | None = Query(None, description="Pagination cursor"),
        page_size: int = Query(
            DEFAULT_PAGE_SIZE,
            ge=1,
            le=MAX_PAGE_SIZE,
            description=f"Items per page (max {MAX_PAGE_SIZE})",
        ),
        direction: str = Query(
            "next",
            pattern="^(next|prev)$",
            description="Pagination direction",
        ),
    ):
        self.cursor = cursor
        self.page_size = page_size
        self.direction = direction


def get_cursor_pagination(
    cursor: str | None = Query(None, description="Pagination cursor"),
    page_size: int = Query(
        DEFAULT_PAGE_SIZE,
        ge=1,
        le=MAX_PAGE_SIZE,
        description=f"Items per page (max {MAX_PAGE_SIZE})",
    ),
    direction: str = Query(
        "next",
        pattern="^(next|prev)$",
        description="Pagination direction",
    ),
) -> CursorPaginationParams:
    """Dependency for cursor-based pagination."""
    return CursorPaginationParams(
        cursor=cursor,
        page_size=page_size,
        direction=direction,
    )


class CursorPaginatedResponse(BaseModel, Generic[T]):
    """Cursor-based paginated response format."""

    items: list[T] = Field(description="List of items")
    next_cursor: str | None = Field(None, description="Cursor for next page")
    prev_cursor: str | None = Field(None, description="Cursor for previous page")
    has_more: bool = Field(description="Whether there are more items")
    page_size: int = Field(description="Items per page")


class PageMetadata(BaseModel):
    """Metadata for paginated responses."""

    total: int = Field(description="Total count (if available)")
    page: int = Field(description="Current page")
    page_size: int = Field(description="Items per page")
    sort_by: str | None = Field(None, description="Sort field")
    sort_order: str = Field("desc", description="Sort order")


def parse_sort_field(
    sort_by: str | None,
    allowed_fields: set[str],
    default: str = "created_at",
) -> str:
    """Parse and validate sort field.

    Args:
        sort_by: Requested sort field
        allowed_fields: Set of allowed sort fields
        default: Default sort field if none specified

    Returns:
        Validated sort field
    """
    if not sort_by:
        return default

    # Handle prefixed fields like "-created_at" for descending
    field = sort_by.lstrip("-+")

    if field not in allowed_fields:
        return default

    return sort_by
