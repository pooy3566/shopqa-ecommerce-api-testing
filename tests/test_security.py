"""Regression tests for the fixed vulnerabilities documented in SECURITY-AUDIT.md.

Each test guards one finding. Reverting the corresponding fix commit should turn
its test red. Run just these with:  pytest -m security
"""
import pytest
from pydantic import ValidationError

from app.core.config import Settings

pytestmark = pytest.mark.security


# --- ECOM-02: hardcoded / weak SECRET_KEY (CWE-798) --------------------------

def test_settings_rejects_known_placeholder_secret(monkeypatch):
    """Booting with a known placeholder signing key must fail loudly."""
    monkeypatch.setenv("SECRET_KEY", "your-secret-key-change-in-production")
    with pytest.raises(ValidationError):
        Settings(_env_file=None)


def test_settings_rejects_short_secret(monkeypatch):
    monkeypatch.setenv("SECRET_KEY", "tooshort")
    with pytest.raises(ValidationError):
        Settings(_env_file=None)


def test_settings_requires_secret_key(monkeypatch):
    """No SECRET_KEY at all must fail, not fall back to a default."""
    monkeypatch.delenv("SECRET_KEY", raising=False)
    with pytest.raises(ValidationError):
        Settings(_env_file=None)


def test_settings_accepts_strong_secret(monkeypatch):
    monkeypatch.setenv("SECRET_KEY", "x" * 48)
    assert Settings(_env_file=None).SECRET_KEY == "x" * 48


# --- ECOM-01: privilege escalation via self-registration (CWE-269) -----------

def test_register_rejects_is_admin_field(client):
    """A registration body carrying is_admin must be refused, not silently ignored."""
    resp = client.post(
        "/api/v1/auth/register",
        json={
            "email": "escalate@example.com",
            "username": "escalate",
            "full_name": "Escalation Attempt",
            "password": "LongEnoughPass123",
            "is_admin": True,
        },
    )
    assert resp.status_code == 422


def test_register_creates_non_admin_user(client):
    """A normal registration succeeds and the account is not an admin."""
    resp = client.post(
        "/api/v1/auth/register",
        json={
            "email": "normal@example.com",
            "username": "normaluser",
            "full_name": "Normal User",
            "password": "LongEnoughPass123",
        },
    )
    assert resp.status_code == 201
    assert resp.json()["is_admin"] is False


def test_non_admin_cannot_list_all_orders(client, db_session, test_user, test_admin_user,
                                           auth_headers):
    """A non-admin sees only their own orders, never everyone's."""
    from app.models.order import Order

    db_session.add(Order(user_id=test_admin_user.id, total_amount=999.0, status=None))
    db_session.add(Order(user_id=test_user.id, total_amount=10.0, status=None))
    db_session.commit()

    resp = client.get("/api/v1/orders/", headers=auth_headers)
    assert resp.status_code == 200
    owners = {o["user_id"] for o in resp.json()}
    assert owners <= {test_user.id}


# --- ECOM-03: JWT verification + malformed subject 500 (CWE-347, CWE-703) ----

def _forge(sub, **overrides):
    """Build a token, letting a test override the signing key or claims."""
    from datetime import datetime, timedelta, timezone
    from jose import jwt
    from app.core.config import settings

    now = datetime.now(timezone.utc)
    claims = {
        "sub": sub,
        "exp": now + timedelta(minutes=5),
        "nbf": now,
        "iat": now,
        "iss": settings.JWT_ISSUER,
        "aud": settings.JWT_AUDIENCE,
    }
    claims.update(overrides.get("claims", {}))
    key = overrides.get("key", settings.SECRET_KEY)
    return jwt.encode(claims, key, algorithm=settings.ALGORITHM)


def test_token_signed_with_wrong_key_is_rejected(client, test_user):
    token = _forge(str(test_user.id), key="a-different-key-that-is-long-enough-xxxx")
    resp = client.get("/api/v1/orders/", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 401


def test_token_with_wrong_audience_is_rejected(client, test_user):
    token = _forge(str(test_user.id), claims={"aud": "some-other-service"})
    resp = client.get("/api/v1/orders/", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 401


def test_expired_token_is_rejected(client, test_user):
    from datetime import datetime, timedelta, timezone
    token = _forge(str(test_user.id),
                   claims={"exp": datetime.now(timezone.utc) - timedelta(seconds=1)})
    resp = client.get("/api/v1/orders/", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 401


def test_malformed_subject_returns_401_not_500(client):
    """A validly-signed token with a non-numeric sub must be 401, never 500."""
    token = _forge("not-an-integer")
    resp = client.get("/api/v1/orders/", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 401


def test_order_summary_scopes_to_owner(client, db_session, test_user, test_admin_user,
                                       auth_headers, admin_auth_headers):
    """The raw-SQL summary must honour the tenant boundary in its WHERE clause.

    Guards the predicate `WHERE (:is_admin = true OR o.user_id = :user_id)` in
    app/api/v1/orders.py. A non-admin must not see the admin's order or email.
    """
    from app.models.order import Order

    db_session.add(Order(user_id=test_admin_user.id, total_amount=500.0, status=None))
    db_session.add(Order(user_id=test_user.id, total_amount=20.0, status=None))
    db_session.commit()

    as_user = client.get("/api/v1/orders/summary", headers=auth_headers).json()
    emails_user = {row["user_email"] for row in as_user}
    assert emails_user <= {test_user.email}
    assert test_admin_user.email not in emails_user

    as_admin = client.get("/api/v1/orders/summary", headers=admin_auth_headers).json()
    emails_admin = {row["user_email"] for row in as_admin}
    assert {test_user.email, test_admin_user.email} <= emails_admin


# --- ECOM-04: login rate limiting (CWE-307) ----------------------------------

def test_login_locks_out_after_repeated_failures(client, test_user):
    """Six bad passwords in a row: the sixth is throttled with 429."""
    bad = {"username": test_user.username, "password": "wrong-password"}
    for _ in range(5):
        assert client.post("/api/v1/auth/login", data=bad).status_code == 401
    throttled = client.post("/api/v1/auth/login", data=bad)
    assert throttled.status_code == 429
    assert "Retry-After" in throttled.headers


def test_correct_login_not_affected_by_other_users_failures(client, test_user):
    """A fresh (ip, username) pair with correct credentials still logs in."""
    resp = client.post(
        "/api/v1/auth/login",
        data={"username": test_user.username, "password": "testpassword123"},
    )
    assert resp.status_code == 200


# --- ECOM-05: user enumeration on registration (CWE-204) ---------------------

def test_duplicate_registration_does_not_confirm_account(client, test_user):
    resp = client.post(
        "/api/v1/auth/register",
        json={
            "email": test_user.email,
            "username": test_user.username,
            "password": "LongEnoughPass123",
            "full_name": "Dupe",
        },
    )
    assert resp.status_code == 409
    assert "already registered" not in resp.json()["detail"]
    assert "email" not in resp.json()["detail"].lower()


# --- ECOM-06: CORS not a wildcard with credentials (CWE-942) -----------------

def test_cors_rejects_unlisted_origin(client):
    resp = client.get(
        "/api/v1/products/",
        headers={"Origin": "https://evil.example",
                 "Access-Control-Request-Method": "GET"},
    )
    assert resp.headers.get("access-control-allow-origin") != "*"
    assert resp.headers.get("access-control-allow-origin") != "https://evil.example"
