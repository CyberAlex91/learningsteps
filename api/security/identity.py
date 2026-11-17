"""Validate delegated Entra access tokens for this API, never Foundry tokens.

This module is not wired into the live journal routes yet. Test key providers
are constructor arguments for isolated tests, never request/header switches.
"""

import json
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from uuid import UUID

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2AuthorizationCodeBearer
from jwt import PyJWKClient
from jwt.exceptions import (
    InvalidTokenError,
    PyJWKClientConnectionError,
    PyJWKClientError,
)


@dataclass(frozen=True)
class AuthSettings:
    tenant_id: str
    api_client_id: str
    swagger_client_id: str

    def __post_init__(self):
        for field in ("tenant_id", "api_client_id", "swagger_client_id"):
            object.__setattr__(self, field, str(UUID(getattr(self, field))))

    @classmethod
    def load(cls, path: Path | None = None) -> "AuthSettings":
        """Read public application identifiers only; no secrets in this file."""
        config = path or Path(__file__).with_name("entra.json")
        return cls(**json.loads(config.read_text(encoding="utf-8")))

    @property
    def issuer(self) -> str:
        return f"https://login.microsoftonline.com/{self.tenant_id}/v2.0"

    @property
    def jwks_url(self) -> str:
        return (
            f"https://login.microsoftonline.com/{self.tenant_id}"
            "/discovery/v2.0/keys"
        )

    @property
    def scope(self) -> str:
        return f"api://{self.api_client_id}/access_as_user"


@dataclass(frozen=True)
class Principal:
    """Immutable ownership key derived only from a verified access token."""

    tenant_id: str
    object_id: str


def unauthorized() -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid or expired LearningSteps access token",
        headers={"WWW-Authenticate": "Bearer"},
    )


class EntraTokenVerifier:
    def __init__(
        self,
        settings: AuthSettings,
        key_provider: Callable[[str], Any] | None = None,
    ):
        self.settings = settings
        if key_provider is None:
            # The URL comes from trusted configuration, never the JWT's jku/x5u.
            self._jwks = PyJWKClient(
                settings.jwks_url,
                cache_jwk_set=True,
                lifespan=300,
                timeout=5,
            )
            self._key_provider = self._entra_signing_key
        else:
            self._key_provider = key_provider

    def _entra_signing_key(self, token: str) -> Any:
        return self._jwks.get_signing_key_from_jwt(token).key

    def verify(self, token: str) -> Principal:
        try:
            if not isinstance(token, str) or len(token) > 16_384:
                raise InvalidTokenError()
            header = jwt.get_unverified_header(token)
            if (
                header.get("alg") != "RS256"
                or not isinstance(header.get("kid"), str)
                or not 1 <= len(header["kid"]) <= 256
            ):
                raise InvalidTokenError()
            key = self._key_provider(token)
            claims = jwt.decode(
                token,
                key,
                algorithms=["RS256"],
                audience=self.settings.api_client_id,
                issuer=self.settings.issuer,
                leeway=30,
                options={
                    "strict_aud": True,
                    "require": [
                        "exp", "iat", "nbf", "iss", "aud", "tid", "oid",
                        "ver", "azp",
                    ],
                },
            )
            tenant_id = str(UUID(claims["tid"]))
            object_id = str(UUID(claims["oid"]))
            if tenant_id != self.settings.tenant_id or claims["ver"] != "2.0":
                raise InvalidTokenError()
        except PyJWKClientConnectionError:
            # Never return raw SDK exceptions, tokens or request bodies.
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Identity provider temporarily unavailable",
            ) from None
        except (InvalidTokenError, PyJWKClientError, ValueError, TypeError, AttributeError):
            raise unauthorized() from None

        scopes = claims.get("scp")
        if (
            not isinstance(scopes, str)
            or "access_as_user" not in scopes.split()
            or claims.get("idtyp") not in (None, "user")
            or claims["azp"] != self.settings.swagger_client_id
        ):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Delegated LearningSteps permission required",
            )
        return Principal(tenant_id=tenant_id, object_id=object_id)


def create_current_user_dependency(
    settings: AuthSettings,
    verifier: EntraTokenVerifier | None = None,
) -> Callable[..., Principal]:
    """Sync dependency: JWKS I/O runs in FastAPI's dependency threadpool."""
    token_verifier = verifier or EntraTokenVerifier(settings)
    authority = f"https://login.microsoftonline.com/{settings.tenant_id}/oauth2/v2.0"
    bearer = OAuth2AuthorizationCodeBearer(
        authorizationUrl=f"{authority}/authorize",
        tokenUrl=f"{authority}/token",
        scopes={settings.scope: "Use LearningSteps as the signed-in user"},
    )

    def current_user(token: str = Depends(bearer)) -> Principal:
        return token_verifier.verify(token)

    return current_user
