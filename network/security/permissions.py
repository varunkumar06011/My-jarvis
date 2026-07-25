from enum import Enum, auto
from typing import Callable


class Permission(Enum):
    READ = "read"
    CHAT = "chat"
    VOICE = "voice"
    EXECUTE_TOOLS = "execute_tools"
    SETTINGS = "settings"
    PLUGINS = "plugins"
    ADMIN = "admin"


ALL_PERMISSIONS = [p.value for p in Permission]


def has_permission(user_permissions: list[str], required: Permission) -> bool:
    if Permission.ADMIN.value in user_permissions:
        return True
    return required.value in user_permissions


def require_permission(required: Permission) -> Callable:
    from fastapi import HTTPException, status

    def checker(user_permissions: list[str]):
        if not has_permission(user_permissions, required):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Permission '{required.value}' required",
            )
        return True

    return checker
