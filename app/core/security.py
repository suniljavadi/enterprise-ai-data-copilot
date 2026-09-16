import json
from enum import Enum

from fastapi import Depends, Header
from pydantic import BaseModel

from app.core.config import get_settings
from app.core.exceptions import AppError


class AuthenticationError(AppError):
    status_code = 401
    detail = "Missing or invalid API key"


class AuthorizationError(AppError):
    status_code = 403
    detail = "You do not have permission to perform this action"


class Role(str, Enum):
    ADMIN = "admin"
    ANALYST = "analyst"
    VIEWER = "viewer"


class Principal(BaseModel):
    api_key: str
    name: str
    role: Role


def _load_api_key_directory() -> dict[str, Principal]:
    settings = get_settings()
    try:
        raw = json.loads(settings.api_keys)
    except json.JSONDecodeError as exc:
        raise ValueError(f"API_KEYS is not valid JSON: {exc}") from exc

    directory: dict[str, Principal] = {}
    for api_key, info in raw.items():
        directory[api_key] = Principal(api_key=api_key, name=info["name"], role=Role(info["role"]))
    return directory


def get_current_principal(x_api_key: str | None = Header(default=None, alias="X-API-Key")) -> Principal:
    if not x_api_key:
        raise AuthenticationError("Missing X-API-Key header")
    principal = _load_api_key_directory().get(x_api_key)
    if principal is None:
        raise AuthenticationError("Invalid API key")
    return principal


def require_role(*allowed_roles: Role):
    """FastAPI dependency factory: only principals with one of the allowed roles may proceed."""

    def _dependency(principal: Principal = Depends(get_current_principal)) -> Principal:
        if principal.role not in allowed_roles:
            raise AuthorizationError(f"Role '{principal.role.value}' is not permitted to perform this action")
        return principal

    return _dependency
