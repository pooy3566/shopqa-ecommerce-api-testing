from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from app.db.base import get_db
from app.core.security import verify_password, create_access_token
from app.core import ratelimit
from app.schemas.user import UserCreate, UserResponse, Token
from app.crud import user as crud_user

router = APIRouter()


def _client_ip(request: Request) -> str:
    return request.client.host if request.client else "unknown"


@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
def register_user(user_data: UserCreate, db: Session = Depends(get_db)):
    """Register a new user."""
    # Generic message and status: revealing whether an email or username is
    # already taken lets an attacker enumerate accounts (CWE-204).
    if crud_user.get_user_by_email(db, user_data.email) or \
       crud_user.get_user_by_username(db, user_data.username):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Registration could not be completed",
        )
    return crud_user.create_user(db, user_data)


@router.post("/login", response_model=Token)
def login(
    request: Request,
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db),
):
    """Login and get access token."""
    ip = _client_ip(request)
    username = form_data.username

    # Throttle online password guessing (CWE-307).
    if ratelimit.is_locked(ip, username):
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Too many failed login attempts. Try again later.",
            headers={"Retry-After": str(ratelimit.retry_after_seconds())},
        )

    user = crud_user.get_user_by_username(db, username)
    if not user or not verify_password(form_data.password, user.hashed_password):
        ratelimit.record_failure(ip, username)
        raise HTTPException(
            status_code=401,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if not user.is_active:
        raise HTTPException(status_code=400, detail="Inactive user")

    ratelimit.clear(ip, username)
    access_token = create_access_token(data={"sub": str(user.id)})
    return {"access_token": access_token, "token_type": "bearer"}
