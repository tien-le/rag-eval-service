"""Auth0 integration service."""

import json
from typing import Any, Protocol
from urllib.parse import urlencode

import httpx
from jwcrypto import jwk, jwt

from app.core.config.logging import get_logger
from app.core.config.settings import Settings, get_settings

logger = get_logger(__name__)


class TokenPayload:
    """Validated token payload."""

    def __init__(self, claims: dict[str, Any]):
        self.sub = claims.get("sub")
        self.email = claims.get("email")
        self.name = claims.get("name")
        self.permissions = claims.get("permissions", [])
        self.tenant_id = claims.get("tenant_id") or claims.get("https://tenant/id")
        self.claims = claims


class Auth0Service(Protocol):
    """Protocol for Auth0 service."""

    async def validate_token(self, token: str) -> TokenPayload:
        """Validate JWT token and return claims."""
        ...

    async def get_userinfo(self, token: str) -> dict[str, Any]:
        """Get user info from Auth0."""
        ...


class Auth0ServiceImpl:
    """Auth0 service implementation."""

    def __init__(self, settings: Settings | None = None):
        self.settings = settings or get_settings()
        self._jwks: dict[str, Any] | None = None
        self._jwks_client: Any | None = None

    async def _get_jwks(self) -> dict[str, Any]:
        """Fetch JWKS from Auth0."""
        if self._jwks is not None:
            return self._jwks

        domain = getattr(self.settings, "AUTH0_DOMAIN", None)
        if not domain:
            raise ValueError("AUTH0_DOMAIN not configured")

        jwks_url = f"https://{domain}/.well-known/jwks.json"

        async with httpx.AsyncClient() as client:
            response = await client.get(jwks_url, timeout=10.0)
            response.raise_for_status()
            self._jwks = response.json()

        return self._jwks

    async def validate_token(self, token: str) -> TokenPayload:
        """Validate JWT token against Auth0 JWKS.

        Args:
            token: JWT access token

        Returns:
            TokenPayload with validated claims

        Raises:
            ValueError: If token is invalid
        """
        domain = getattr(self.settings, "AUTH0_DOMAIN", None)
        audience = getattr(self.settings, "AUTH0_AUDIENCE", None)

        if not domain:
            raise ValueError("AUTH0_DOMAIN not configured")

        try:
            # Get JWKS
            jwks = await self._get_jwks()

            # Create key set
            key_set = jwk.JWKSet()
            for key_data in jwks.get("keys", []):
                key_set.add(jwk.JWK(**key_data))

            # Validate token
            token_obj = jwt.JWT(key=key_set, jwt=token)
            claims = json.loads(token_obj.claims)

            # Verify audience if configured
            if audience and claims.get("aud") != audience:
                raise ValueError("Invalid token audience")

            # Verify issuer
            expected_issuer = f"https://{domain}/"
            if claims.get("iss") != expected_issuer:
                raise ValueError("Invalid token issuer")

            return TokenPayload(claims)

        except Exception as e:
            logger.warning("auth0_token_validation_failed error=%s", str(e))
            raise ValueError(f"Token validation failed: {e}") from e

    async def get_userinfo(self, token: str) -> dict[str, Any]:
        """Get user info from Auth0 userinfo endpoint.

        Args:
            token: Access token

        Returns:
            User info dictionary
        """
        domain = getattr(self.settings, "AUTH0_DOMAIN", None)
        if not domain:
            raise ValueError("AUTH0_DOMAIN not configured")

        userinfo_url = f"https://{domain}/userinfo"

        async with httpx.AsyncClient() as client:
            response = await client.get(
                userinfo_url,
                headers={"Authorization": f"Bearer {token}"},
                timeout=10.0,
            )
            response.raise_for_status()
            return response.json()

    def get_authorize_url(
        self,
        redirect_uri: str,
        state: str | None = None,
        scope: str = "openid profile email",
    ) -> str:
        """Get Auth0 authorize URL for authorization code flow.

        Args:
            redirect_uri: Callback URL
            state: Optional state parameter
            scope: OAuth scopes

        Returns:
            Authorization URL
        """
        domain = getattr(self.settings, "AUTH0_DOMAIN", None)
        client_id = getattr(self.settings, "AUTH0_CLIENT_ID", None)

        if not domain or not client_id:
            raise ValueError("AUTH0_DOMAIN and AUTH0_CLIENT_ID required")

        params = {
            "response_type": "code",
            "client_id": client_id,
            "redirect_uri": redirect_uri,
            "scope": scope,
        }
        if state:
            params["state"] = state

        return f"https://{domain}/authorize?{urlencode(params)}"

    async def exchange_code(self, code: str, redirect_uri: str) -> dict[str, Any]:
        """Exchange authorization code for tokens.

        Args:
            code: Authorization code
            redirect_uri: Callback URL

        Returns:
            Token response
        """
        domain = getattr(self.settings, "AUTH0_DOMAIN", None)
        client_id = getattr(self.settings, "AUTH0_CLIENT_ID", None)
        client_secret = getattr(self.settings, "AUTH0_CLIENT_SECRET", None)

        if not all([domain, client_id, client_secret]):
            raise ValueError("Auth0 not fully configured")

        token_url = f"https://{domain}/oauth/token"

        payload = {
            "grant_type": "authorization_code",
            "client_id": client_id,
            "client_secret": client_secret.get_secret_value() if hasattr(client_secret, "get_secret_value") else client_secret,
            "code": code,
            "redirect_uri": redirect_uri,
        }

        async with httpx.AsyncClient() as client:
            response = await client.post(token_url, json=payload, timeout=10.0)
            response.raise_for_status()
            return response.json()


# Singleton instance
_auth0_service: Auth0ServiceImpl | None = None


def get_auth0_service() -> Auth0Service:
    """Get Auth0 service singleton."""
    global _auth0_service
    if _auth0_service is None:
        _auth0_service = Auth0ServiceImpl()
    return _auth0_service
