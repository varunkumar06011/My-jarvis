from typing import Optional

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from configs.config import API_DEFAULT_KEY
from network.security.api_keys import api_key_manager
from network.security.audit import audit_logger
from network.security.jwt import jwt_manager

security_scheme = HTTPBearer(auto_error=False)


async def authenticate(
    request: Request,
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security_scheme),
) -> dict:
    client_ip = request.client.host if request.client else "unknown"

    if credentials is None:
        audit_logger.auth_failed(client_ip)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing authentication credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )

    token = credentials.credentials

    # Try API key first
    if api_key_manager.validate(token):
        name = api_key_manager.get_name(token) or "unknown"
        permissions = api_key_manager.get_permissions(token)
        return {
            "client": name,
            "client_ip": client_ip,
            "permissions": permissions,
            "auth_method": "api_key",
        }

    # Try JWT
    payload = jwt_manager.verify_token(token)
    if payload is not None:
        return {
            "client": payload.get("sub", "unknown"),
            "client_ip": client_ip,
            "permissions": payload.get("permissions", []),
            "auth_method": "jwt",
        }

    # Fallback: dev key (only when token matches the default)
    if token == API_DEFAULT_KEY:
        return {
            "client": "dev",
            "client_ip": client_ip,
            "permissions": ["read", "chat", "voice", "execute_tools", "settings", "plugins", "admin"],
            "auth_method": "dev_key",
        }

    audit_logger.auth_failed(client_ip)
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid API key or token",
        headers={"WWW-Authenticate": "Bearer"},
    )


def require_perm(permission: str):
    from network.security.permissions import Permission

    perm = Permission(permission)

    async def checker(auth: dict = Depends(authenticate)) -> dict:
        from network.security.permissions import has_permission

        if not has_permission(auth["permissions"], perm):
            audit_logger.permission_denied(auth["client"], permission)
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Permission '{permission}' required",
            )
        return auth

    return checker
