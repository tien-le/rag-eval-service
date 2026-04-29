"""Permission and RBAC management."""

from enum import Enum


class Permission(str, Enum):
    """Application permissions."""

    # Evaluation permissions
    EVAL_READ = "eval:read"
    EVAL_WRITE = "eval:write"
    EVAL_DELETE = "eval:delete"
    EVAL_ADMIN = "eval:admin"

    # Workflow permissions
    WORKFLOW_READ = "workflow:read"
    WORKFLOW_WRITE = "workflow:write"
    WORKFLOW_PUBLISH = "workflow:publish"
    WORKFLOW_DELETE = "workflow:delete"

    # RAG permissions
    RAG_READ = "rag:read"
    RAG_WRITE = "rag:write"
    RAG_INDEX = "rag:index"

    # Agent permissions
    AGENT_READ = "agent:read"
    AGENT_WRITE = "agent:write"
    AGENT_EXECUTE = "agent:execute"

    # Prompt permissions
    PROMPT_READ = "prompt:read"
    PROMPT_WRITE = "prompt:write"
    PROMPT_PUBLISH = "prompt:publish"

    # Admin permissions
    ADMIN_READ = "admin:read"
    ADMIN_WRITE = "admin:write"
    ADMIN_DELETE = "admin:delete"
    ADMIN_SUPER = "admin:*"


class Role:
    """Role definition with permissions."""

    def __init__(self, name: str, permissions: list[Permission | str]):
        self.name = name
        self.permissions = {
            p.value if isinstance(p, Permission) else p for p in permissions
        }

    def has_permission(self, permission: Permission | str) -> bool:
        """Check if role has a specific permission."""
        perm = permission.value if isinstance(permission, Permission) else permission
        return (
            perm in self.permissions or Permission.ADMIN_SUPER.value in self.permissions
        )


# Predefined roles
ROLE_VIEWER = Role(
    "viewer", [Permission.EVAL_READ, Permission.WORKFLOW_READ, Permission.RAG_READ]
)

ROLE_EDITOR = Role(
    "editor",
    [
        Permission.EVAL_READ,
        Permission.EVAL_WRITE,
        Permission.WORKFLOW_READ,
        Permission.WORKFLOW_WRITE,
        Permission.RAG_READ,
        Permission.RAG_WRITE,
        Permission.PROMPT_READ,
        Permission.PROMPT_WRITE,
    ],
)

ROLE_ADMIN = Role(
    "admin",
    [
        Permission.EVAL_READ,
        Permission.EVAL_WRITE,
        Permission.EVAL_DELETE,
        Permission.WORKFLOW_READ,
        Permission.WORKFLOW_WRITE,
        Permission.WORKFLOW_PUBLISH,
        Permission.WORKFLOW_DELETE,
        Permission.RAG_READ,
        Permission.RAG_WRITE,
        Permission.RAG_INDEX,
        Permission.AGENT_READ,
        Permission.AGENT_WRITE,
        Permission.AGENT_EXECUTE,
        Permission.PROMPT_READ,
        Permission.PROMPT_WRITE,
        Permission.PROMPT_PUBLISH,
        Permission.ADMIN_READ,
        Permission.ADMIN_WRITE,
    ],
)

ROLE_SUPER_ADMIN = Role("super_admin", [Permission.ADMIN_SUPER])

PREDEFINED_ROLES = {
    "viewer": ROLE_VIEWER,
    "editor": ROLE_EDITOR,
    "admin": ROLE_ADMIN,
    "super_admin": ROLE_SUPER_ADMIN,
}


class PermissionChecker:
    """Check permissions for a user or service."""

    def __init__(self, permissions: list[str]):
        self.permissions = set(permissions)

    def check(self, required: Permission | str | list[Permission | str]) -> bool:
        """Check if required permissions are satisfied.

        Args:
            required: Required permission(s)

        Returns:
            True if all required permissions are granted
        """
        if isinstance(required, list):
            return all(self._has_permission(r) for r in required)
        return self._has_permission(required)

    def _has_permission(self, permission: Permission | str) -> bool:
        """Check single permission."""
        perm = permission.value if isinstance(permission, Permission) else permission

        # Super admin has all permissions
        if Permission.ADMIN_SUPER.value in self.permissions:
            return True

        # Wildcard check (e.g., "eval:*" matches "eval:read")
        if ":" in perm:
            resource, action = perm.rsplit(":", 1)
            wildcard = f"{resource}:*"
            if wildcard in self.permissions:
                return True

        return perm in self.permissions

    def any_of(self, options: list[Permission | str]) -> bool:
        """Check if any of the permissions are granted."""
        return any(self._has_permission(p) for p in options)


def get_role_permissions(role_name: str) -> list[str]:
    """Get permissions for a predefined role."""
    role = PREDEFINED_ROLES.get(role_name)
    return list(role.permissions) if role else []


def has_permission(
    user_permissions: list[str],
    required: Permission | str | list[Permission | str],
) -> bool:
    """Convenience function to check if user has required permissions."""
    checker = PermissionChecker(user_permissions)
    return checker.check(required)
