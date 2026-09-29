"""Provision an administrator out of band.

Self-registration can no longer grant admin (see CWE-269 fix). This is the
supported way to create one: it runs against the configured database and sets
is_admin explicitly, so the privilege is granted by someone with shell and
database access, never by an anonymous HTTP caller.

    python scripts/create_admin.py --email admin@example.com --username admin

The password is read interactively (never passed on the command line, where it
would land in shell history and the process table).
"""
import argparse
import getpass
import sys

from app.db.base import get_session_factory
from app.core.security import get_password_hash
from app.crud.user import get_user_by_username, get_user_by_email
from app.models.user import User


def main() -> int:
    parser = argparse.ArgumentParser(description="Create an admin user.")
    parser.add_argument("--email", required=True)
    parser.add_argument("--username", required=True)
    parser.add_argument("--full-name", default=None)
    args = parser.parse_args()

    session = get_session_factory()()
    try:
        if get_user_by_username(session, args.username):
            print(f"error: username {args.username!r} already exists", file=sys.stderr)
            return 1
        if get_user_by_email(session, args.email):
            print(f"error: email {args.email!r} already exists", file=sys.stderr)
            return 1

        password = getpass.getpass("Admin password: ")
        if len(password) < 12:
            print("error: choose a password of at least 12 characters", file=sys.stderr)
            return 1
        if getpass.getpass("Confirm password: ") != password:
            print("error: passwords do not match", file=sys.stderr)
            return 1

        admin = User(
            email=args.email,
            username=args.username,
            full_name=args.full_name,
            hashed_password=get_password_hash(password),
            is_active=True,
            is_admin=True,
        )
        session.add(admin)
        session.commit()
        print(f"created admin {args.username!r} ({args.email})")
        return 0
    finally:
        session.close()


if __name__ == "__main__":
    sys.exit(main())
