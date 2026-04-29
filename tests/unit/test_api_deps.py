"""Tests for API dependencies."""

import pytest

from app.api.deps.auth import CurrentUser
from app.api.deps.pagination import PaginationParams, PaginatedResponse
from app.api.deps.tenant import TenantContext


class TestCurrentUser:
    """Test CurrentUser class."""

    def test_has_permission(self) -> None:
        """Test permission checking."""
        user = CurrentUser(
            user_id="user123",
            permissions=["eval:read", "eval:write"],
        )

        assert user.has_permission("eval:read") is True
        assert user.has_permission("eval:write") is True
        assert user.has_permission("admin:read") is False

    def test_has_any_permission(self) -> None:
        """Test checking any of multiple permissions."""
        user = CurrentUser(
            user_id="user123",
            permissions=["eval:read"],
        )

        assert user.has_any_permission(["eval:read", "admin:read"]) is True
        assert user.has_any_permission(["admin:read", "admin:write"]) is False


class TestPaginationParams:
    """Test PaginationParams class."""

    def test_offset_calculation(self) -> None:
        """Test offset calculation."""
        params = PaginationParams(page=3, page_size=20)

        assert params.offset == 40  # (3-1) * 20
        assert params.limit == 20

    def test_first_page_offset_zero(self) -> None:
        """Test that first page has zero offset."""
        params = PaginationParams(page=1, page_size=20)

        assert params.offset == 0


class TestPaginatedResponse:
    """Test PaginatedResponse class."""

    def test_create_paginated_response(self) -> None:
        """Test creating paginated response."""
        items = ["item1", "item2", "item3"]
        total = 25
        pagination = PaginationParams(page=2, page_size=10)

        response = PaginatedResponse.create(items, total, pagination)

        assert response.items == items
        assert response.total == 25
        assert response.page == 2
        assert response.page_size == 10
        assert response.pages == 3  # ceil(25/10)
        assert response.has_next is True
        assert response.has_prev is True

    def test_last_page_has_no_next(self) -> None:
        """Test that last page has no next."""
        items = ["item1"]
        total = 11
        pagination = PaginationParams(page=2, page_size=10)

        response = PaginatedResponse.create(items, total, pagination)

        assert response.has_next is False
        assert response.has_prev is True


class TestTenantContext:
    """Test TenantContext class."""

    def test_has_feature(self) -> None:
        """Test feature checking."""
        tenant = TenantContext(
            tenant_id="tenant1",
            features=["eval:read", "eval:write"],
        )

        assert tenant.has_feature("eval:read") is True
        assert tenant.has_feature("admin:read") is False

    def test_has_feature_wildcard(self) -> None:
        """Test that wildcard grants all features."""
        tenant = TenantContext(
            tenant_id="tenant1",
            features=["*"],
        )

        assert tenant.has_feature("any_feature") is True

    def test_get_quota(self) -> None:
        """Test quota retrieval."""
        tenant = TenantContext(
            tenant_id="tenant1",
            quota_limits={"evaluations_per_hour": 500},
        )

        assert tenant.get_quota("evaluations_per_hour") == 500
        assert tenant.get_quota("missing_quota", default=100) == 100
