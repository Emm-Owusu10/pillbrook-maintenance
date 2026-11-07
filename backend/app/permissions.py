"""Who may do what (Chapter Three, Table 3.3). Plain data with no web code, so it is easy to test."""
from enum import StrEnum
from types import MappingProxyType


class Permission(StrEnum):
    SUBMIT_REQUEST = "submit_request"
    EDIT_OWN_REQUEST = "edit_own_request"
    VIEW_OWN_REQUESTS = "view_own_requests"
    CONFIRM_OWN_REQUEST = "confirm_own_request"
    VIEW_OWN_NOTIFICATIONS = "view_own_notifications"
    VIEW_ALL_REQUESTS = "view_all_requests"
    HANDLE_REQUESTS = "handle_requests"  # start action, record action, mark Fixed
    CLOSE_REQUESTS = "close_requests"
    VIEW_REPORTS = "view_reports"
    VIEW_ACCESS_CODE = "view_access_code"
    CHANGE_ACCESS_CODE = "change_access_code"
    MANAGE_USERS = "manage_users"  # list users, assign roles, deactivate, start an assisted reset
    VIEW_AUDIT_LOG = "view_audit_log"


_EVERYONE = frozenset(
    {
        Permission.SUBMIT_REQUEST,
        Permission.EDIT_OWN_REQUEST,
        Permission.VIEW_OWN_REQUESTS,
        Permission.CONFIRM_OWN_REQUEST,
        Permission.VIEW_OWN_NOTIFICATIONS,
    }
)

# Read-only: nothing can change this table while the application runs.
ROLE_PERMISSIONS = MappingProxyType(
    {
        "user": _EVERYONE,
        "manager": _EVERYONE
        | {
            Permission.VIEW_ALL_REQUESTS,
            Permission.HANDLE_REQUESTS,
            Permission.CLOSE_REQUESTS,
            Permission.VIEW_REPORTS,
            Permission.VIEW_ACCESS_CODE,
        },
        "admin": _EVERYONE
        | {
            Permission.VIEW_ALL_REQUESTS,
            Permission.CLOSE_REQUESTS,
            Permission.VIEW_REPORTS,
            Permission.VIEW_ACCESS_CODE,
            Permission.CHANGE_ACCESS_CODE,
            Permission.MANAGE_USERS,
            Permission.VIEW_AUDIT_LOG,
        },
    }
)

# The only addresses anyone may call without signing in. Adding to this list is a deliberate decision.
PUBLIC_ROUTES = MappingProxyType(
    {
        ("GET", "/api/health"): "shows only that the server is up",
        ("POST", "/api/auth/login"): "how people sign in",
        ("POST", "/api/auth/logout"): "works with or without a session, and changes nothing without one",
    }
)


def permissions_for(role: str) -> frozenset[Permission]:
    """An unknown role gets nothing: access is denied unless it is granted."""
    return ROLE_PERMISSIONS.get(role, frozenset())


def has_permission(role: str, permission: Permission) -> bool:
    return permission in permissions_for(role)