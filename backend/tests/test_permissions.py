import pytest

from app.permissions import PUBLIC_ROUTES, ROLE_PERMISSIONS, Permission, has_permission, permissions_for

EVERYONE = {
    "submit_request",
    "edit_own_request",
    "view_own_requests",
    "confirm_own_request",
    "view_own_notifications",
}

# This restates Table 3.3 of Chapter Three, so a change to the rules has to be made in two places.
EXPECTED = {
    "user": EVERYONE,
    "manager": EVERYONE | {"view_all_requests", "handle_requests", "close_requests", "view_reports", "view_access_code"},
    "admin": EVERYONE
    | {
        "view_all_requests",
        "close_requests",
        "view_reports",
        "view_access_code",
        "change_access_code",
        "manage_users",
        "view_audit_log",
    },
}


def _names(role):
    return {permission.value for permission in permissions_for(role)}


def test_the_matrix_matches_chapter_three():
    for role, expected in EXPECTED.items():
        assert _names(role) == expected


def test_every_signed_in_role_can_report_and_follow_its_own_requests():
    for role in EXPECTED:
        assert EVERYONE <= _names(role)


def test_only_the_facility_manager_handles_requests():
    assert has_permission("manager", Permission.HANDLE_REQUESTS)
    assert not has_permission("admin", Permission.HANDLE_REQUESTS)
    assert not has_permission("user", Permission.HANDLE_REQUESTS)


def test_only_the_administrator_manages_users_the_access_code_and_the_audit_log():
    for permission in (Permission.MANAGE_USERS, Permission.CHANGE_ACCESS_CODE, Permission.VIEW_AUDIT_LOG):
        assert has_permission("admin", permission)
        assert not has_permission("manager", permission)
        assert not has_permission("user", permission)


def test_an_unknown_role_gets_nothing():
    assert permissions_for("owner") == frozenset()
    assert permissions_for("") == frozenset()
    assert not has_permission("owner", Permission.SUBMIT_REQUEST)


def test_no_permission_is_left_unassigned():
    assigned = set().union(*ROLE_PERMISSIONS.values())
    assert assigned == set(Permission)


def test_the_rules_cannot_be_changed_while_the_application_runs():
    with pytest.raises(TypeError):
        ROLE_PERMISSIONS["user"] = frozenset(Permission)
    assert all(isinstance(value, frozenset) for value in ROLE_PERMISSIONS.values())


def test_the_roles_match_the_database_rule():
    assert set(ROLE_PERMISSIONS) == {"admin", "manager", "user"}
    assert len(PUBLIC_ROUTES) == 3  # a new open route must be a deliberate decision