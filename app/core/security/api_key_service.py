"""API key management service."""

import hashlib
import secrets
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Protocol

from app.core.config.logging import get_logger

logger = get_logger(__name__)


@dataclass
class APIKey:
    """API key entity."""

    key_id: str
    hashed_key: str
    tenant_id: str
    name: str
    permissions: list[str]
    created_at: datetime
    expires_at: datetime | None
    last_used_at: datetime | None
    is_active: bool
    rate_limit: int  # requests per minute


class APIKeyRepository(Protocol):
    """Protocol for API key repository."""

    async def get_by_key_hash(self, hashed_key: str) -> APIKey | None:
        """Get API key by its hash."""
        ...

    async def create(self, api_key: APIKey) -> APIKey:
        """Store a new API key."""
        ...

    async def update_last_used(self, key_id: str) -> None:
        """Update last used timestamp."""
        ...

    async def revoke(self, key_id: str) -> None:
        """Revoke an API key."""
        ...


class APIKeyService:
    """Service for API key operations."""

    KEY_PREFIX = "rag_eval_"
    KEY_LENGTH = 32

    def __init__(self, repository: APIKeyRepository | None = None):
        self.repository = repository
        self._cache: dict[str, APIKey] = {}  # Simple in-memory cache

    def generate_key(
        self, tenant_id: str, name: str, permissions: list[str] | None = None
    ) -> tuple[str, APIKey]:
        """Generate a new API key.

        Args:
            tenant_id: Tenant identifier
            name: Key name/description
            permissions: List of permissions for this key

        Returns:
            Tuple of (plain_key, APIKey entity)
        """
        # Generate random key
        random_part = secrets.token_urlsafe(self.KEY_LENGTH)
        plain_key = f"{self.KEY_PREFIX}{random_part}"

        # Hash for storage
        hashed_key = self._hash_key(plain_key)

        # Create key entity
        key_id = secrets.token_hex(16)
        api_key = APIKey(
            key_id=key_id,
            hashed_key=hashed_key,
            tenant_id=tenant_id,
            name=name,
            permissions=permissions or ["eval:read"],
            created_at=datetime.now(UTC),
            expires_at=None,
            last_used_at=None,
            is_active=True,
            rate_limit=1000,
        )

        return plain_key, api_key

    def _hash_key(self, key: str) -> str:
        """Hash API key for storage."""
        return hashlib.sha256(key.encode()).hexdigest()

    async def validate_key(self, key: str) -> APIKey | None:
        """Validate an API key.

        Args:
            key: The plain API key to validate

        Returns:
            APIKey if valid, None otherwise
        """
        # Check cache first
        hashed = self._hash_key(key)
        if hashed in self._cache:
            cached = self._cache[hashed]
            if cached.is_active and (
                not cached.expires_at or cached.expires_at > datetime.now(UTC)
            ):
                return cached

        # Check repository if configured
        if self.repository:
            api_key = await self.repository.get_by_key_hash(hashed)
            if api_key and api_key.is_active:
                # Check expiration
                if api_key.expires_at and api_key.expires_at <= datetime.now(UTC):
                    return None

                # Update cache
                self._cache[hashed] = api_key

                # Update last used (async fire-and-forget)
                try:
                    await self.repository.update_last_used(api_key.key_id)
                except Exception as e:
                    logger.warning(
                        "failed_to_update_last_used key_id=%s error=%s",
                        api_key.key_id,
                        str(e),
                    )

                return api_key

        return None

    async def revoke_key(self, key_id: str) -> bool:
        """Revoke an API key."""
        if not self.repository:
            return False

        try:
            await self.repository.revoke(key_id)

            # Remove from cache
            for hashed, key in list(self._cache.items()):
                if key.key_id == key_id:
                    del self._cache[hashed]
                    break

            return True
        except Exception as e:
            logger.error("failed_to_revoke_key key_id=%s error=%s", key_id, str(e))
            return False


# Singleton instance
_api_key_service: APIKeyService | None = None


def get_api_key_service() -> APIKeyService:
    """Get API key service singleton."""
    global _api_key_service
    if _api_key_service is None:
        _api_key_service = APIKeyService()
    return _api_key_service
