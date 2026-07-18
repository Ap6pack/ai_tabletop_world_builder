#!/usr/bin/env python3
# Copyright 2026 Adam Rhys Heaton (Ap6pack) and contributors
# SPDX-License-Identifier: Apache-2.0
"""
Test suite for AuthService — user registration, authentication,
JWT token management, and user CRUD operations.
"""

import sys


def make_service(clean=True):
    """Create an AuthService instance.

    Test isolation is provided by the autouse ``_fresh_db`` fixture (conftest),
    which binds a throwaway SQLite database per test. The ``clean`` argument is
    retained for backward compatibility and is a no-op.
    """
    from api.services.auth_service import AuthService

    return AuthService()


# ── Registration Tests ───────────────────────────────────────────────


def test_register_user():
    """Test 1: Register a user and verify the returned dict."""
    print("\nTest 1: Register user")
    service = make_service()
    user = service.register("alice", "alice@example.com", "password123")
    assert "id" in user, "Missing id"
    assert user["username"] == "alice"
    assert user["email"] == "alice@example.com"
    assert "hashed_password" not in user, "Password hash must not be returned"
    print("  PASS — user registered with expected fields")


def test_register_duplicate_username():
    """Test 2: Duplicate username raises ValueError."""
    print("\nTest 2: Duplicate username")
    service = make_service()
    service.register("bob", "bob@example.com", "password123")
    try:
        service.register("bob", "bob2@example.com", "password123")
        raise AssertionError("Should have raised ValueError")
    except ValueError:
        pass
    print("  PASS — duplicate username rejected")


def test_register_invalid_username():
    """Test 3: Short username raises ValueError."""
    print("\nTest 3: Invalid username (too short)")
    service = make_service()
    try:
        service.register("ab", "short@example.com", "password123")
        raise AssertionError("Should have raised ValueError")
    except ValueError:
        pass
    print("  PASS — short username rejected")


def test_register_invalid_password():
    """Test 4: Short password raises ValueError."""
    print("\nTest 4: Invalid password (too short)")
    service = make_service()
    try:
        service.register("charlie", "charlie@example.com", "short")
        raise AssertionError("Should have raised ValueError")
    except ValueError:
        pass
    print("  PASS — short password rejected")


def test_register_invalid_email():
    """Test 5: Email without @ raises ValueError."""
    print("\nTest 5: Invalid email")
    service = make_service()
    try:
        service.register("dave", "no-at-sign.com", "password123")
        raise AssertionError("Should have raised ValueError")
    except ValueError:
        pass
    print("  PASS — invalid email rejected")


# ── Authentication Tests ─────────────────────────────────────────────


def test_authenticate_success():
    """Test 6: Register then authenticate successfully."""
    print("\nTest 6: Authenticate success")
    service = make_service()
    service.register("eve", "eve@example.com", "securepass1")
    result = service.authenticate("eve", "securepass1")
    assert result is not None, "Authentication should succeed"
    assert result["username"] == "eve"
    assert "hashed_password" not in result
    print("  PASS — authenticated and returned user dict")


def test_authenticate_wrong_password():
    """Test 7: Wrong password returns None."""
    print("\nTest 7: Authenticate wrong password")
    service = make_service()
    service.register("frank", "frank@example.com", "correctpass1")
    result = service.authenticate("frank", "wrongpassword")
    assert result is None, "Wrong password should return None"
    print("  PASS — wrong password returned None")


def test_authenticate_nonexistent_user():
    """Test 8: Unknown user returns None."""
    print("\nTest 8: Authenticate nonexistent user")
    service = make_service()
    result = service.authenticate("ghost_user", "anything123")
    assert result is None, "Nonexistent user should return None"
    print("  PASS — nonexistent user returned None")


# ── Token Tests ──────────────────────────────────────────────────────


def test_create_access_token():
    """Test 9: Access token is a non-empty string."""
    print("\nTest 9: Create access token")
    service = make_service()
    token = service.create_access_token("uid-001", "testuser")
    assert isinstance(token, str) and len(token) > 0
    print("  PASS — access token created")


def test_verify_access_token():
    """Test 10: Verify access token contains expected claims."""
    print("\nTest 10: Verify access token")
    service = make_service()
    token = service.create_access_token("uid-002", "verifyuser", role="admin")
    payload = service.verify_token(token)
    assert payload is not None, "Token should verify"
    assert payload["sub"] == "uid-002"
    assert payload["username"] == "verifyuser"
    assert payload["role"] == "admin"
    print("  PASS — payload has sub, username, role")


def test_verify_invalid_token():
    """Test 11: Garbage token returns None."""
    print("\nTest 11: Verify invalid token")
    service = make_service()
    result = service.verify_token("not.a.real.token")
    assert result is None, "Invalid token should return None"
    print("  PASS — garbage token returned None")


def test_create_and_verify_refresh_token():
    """Test 12: Refresh token contains type='refresh'."""
    print("\nTest 12: Create and verify refresh token")
    service = make_service()
    token = service.create_refresh_token("uid-003")
    payload = service.verify_token(token)
    assert payload is not None, "Refresh token should verify"
    assert payload["type"] == "refresh"
    assert payload["sub"] == "uid-003"
    print("  PASS — refresh token verified with type=refresh")


# ── User CRUD Tests ──────────────────────────────────────────────────


def test_get_user():
    """Test 13: Get user by ID."""
    print("\nTest 13: Get user by ID")
    service = make_service()
    created = service.register("grace", "grace@example.com", "password123")
    fetched = service.get_user(created["id"])
    assert fetched is not None
    assert fetched["id"] == created["id"]
    assert fetched["username"] == "grace"
    assert "hashed_password" not in fetched
    print("  PASS — fetched user matches registered user")


def test_get_user_by_username():
    """Test 14: Look up user by username."""
    print("\nTest 14: Get user by username")
    service = make_service()
    service.register("heidi", "heidi@example.com", "password123")
    fetched = service.get_user_by_username("heidi")
    assert fetched is not None
    assert fetched["username"] == "heidi"
    assert "hashed_password" not in fetched
    print("  PASS — looked up user by username")


def test_update_user():
    """Test 15: Update display_name and verify persistence."""
    print("\nTest 15: Update user")
    service = make_service()
    created = service.register("ivan", "ivan@example.com", "password123")
    updated = service.update_user(created["id"], {"display_name": "Ivan the Great"})
    assert updated is not None
    assert updated["display_name"] == "Ivan the Great"
    refetched = service.get_user(created["id"])
    assert refetched["display_name"] == "Ivan the Great"
    print("  PASS — display_name updated and persisted")


def test_change_password():
    """Test 16: Change password, old fails, new works."""
    print("\nTest 16: Change password")
    service = make_service()
    created = service.register("judy", "judy@example.com", "oldpassword1")
    success = service.change_password(created["id"], "oldpassword1", "newpassword1")
    assert success is True, "Password change should succeed"
    assert service.authenticate("judy", "oldpassword1") is None, "Old password should fail"
    assert service.authenticate("judy", "newpassword1") is not None, "New password should work"
    print("  PASS — password changed; old rejected, new accepted")


def test_list_users():
    """Test 17: List multiple users without passwords."""
    print("\nTest 17: List users")
    service = make_service()
    service.register("user_a", "a@example.com", "password123")
    service.register("user_b", "b@example.com", "password123")
    service.register("user_c", "c@example.com", "password123")
    users = service.list_users()
    assert len(users) >= 3, f"Expected at least 3 users, got {len(users)}"
    for u in users:
        assert "hashed_password" not in u, "Password hash must not appear in list"
    usernames = {u["username"] for u in users}
    assert {"user_a", "user_b", "user_c"}.issubset(usernames)
    print(f"  PASS — listed {len(users)} users, no passwords exposed")


# ── Runner ───────────────────────────────────────────────────────────


if __name__ == "__main__":
    print("=" * 70)
    print("AUTH SERVICE TEST SUITE")
    print("=" * 70)

    all_passed = True
    try:
        test_register_user()
        test_register_duplicate_username()
        test_register_invalid_username()
        test_register_invalid_password()
        test_register_invalid_email()
        test_authenticate_success()
        test_authenticate_wrong_password()
        test_authenticate_nonexistent_user()
        test_create_access_token()
        test_verify_access_token()
        test_verify_invalid_token()
        test_create_and_verify_refresh_token()
        test_get_user()
        test_get_user_by_username()
        test_update_user()
        test_change_password()
        test_list_users()

        print("\n" + "=" * 70)
        print("ALL 17 AUTH SERVICE TESTS PASSED")
        print("=" * 70)
    except Exception as e:
        print(f"\n  FAILED: {e}")
        import traceback

        traceback.print_exc()
        all_passed = False

    sys.exit(0 if all_passed else 1)
