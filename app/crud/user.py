from sqlalchemy.orm import Session
from typing import Optional
from app.models.user import User
from app.schemas.user import UserCreate
from app.core.security import get_password_hash

def get_user_by_username(db: Session, username: str) -> Optional[User]:
    return db.query(User).filter(User.username == username).first()

def get_user_by_email(db: Session, email: str) -> Optional[User]:
    return db.query(User).filter(User.email == email).first()

def create_user(db: Session, user_data: UserCreate) -> User:
    # is_admin is deliberately NOT taken from user_data. Self-registration must
    # always create a non-admin account (CWE-269). Admins are provisioned out of
    # band with scripts/create_admin.py.
    hashed_password = get_password_hash(user_data.password)
    db_user = User(
        email=user_data.email,
        username=user_data.username,
        full_name=user_data.full_name,
        hashed_password=hashed_password,
        is_admin=False,
    )
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user
