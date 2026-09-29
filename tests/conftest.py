import os

# SECRET_KEY has no default in production (CWE-798 fix), so the test process must
# supply one before any app.* import triggers Settings() at module load. This must
# stay above the app imports below.
os.environ.setdefault("SECRET_KEY", "test-only-secret-not-a-real-key-0123456789abcdef")
os.environ.setdefault("DATABASE_URL", "sqlite:///:memory:")
os.environ.setdefault("DEBUG", "false")

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from app.main import app
from app.db.base import Base, get_db
from app.core.security import get_password_hash

# Create in-memory SQLite database for testing
SQLALCHEMY_DATABASE_URL = "sqlite:///:memory:"

engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)

TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


@pytest.fixture(autouse=True)
def _reset_rate_limiter():
    """The login throttle keeps in-process state; isolate it per test (H5)."""
    from app.core import ratelimit
    ratelimit.reset()
    yield
    ratelimit.reset()


@pytest.fixture(scope="function")
def db_session():
    """Create a fresh database session for each test."""
    Base.metadata.create_all(bind=engine)
    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(bind=engine)


@pytest.fixture(scope="function")
def client(db_session):
    """Create a test client with database session override."""
    def override_get_db():
        try:
            yield db_session
        finally:
            db_session.close()
    
    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


@pytest.fixture
def test_user(db_session):
    """Create a test user."""
    from app.models.user import User
    
    user = User(
        email="test@example.com",
        username="testuser",
        full_name="Test User",
        hashed_password=get_password_hash("testpassword123"),
        is_active=True,
        is_admin=False
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


@pytest.fixture
def test_admin_user(db_session):
    """Create a test admin user."""
    from app.models.user import User
    
    admin = User(
        email="admin@example.com",
        username="admin",
        full_name="Admin User",
        hashed_password=get_password_hash("adminpassword123"),
        is_active=True,
        is_admin=True
    )
    db_session.add(admin)
    db_session.commit()
    db_session.refresh(admin)
    return admin


@pytest.fixture
def test_product(db_session):
    """Create a test product."""
    from app.models.product import Product
    
    product = Product(
        name="Test Product",
        description="A test product description",
        price=99.99,
        stock_quantity=100,
        category="Electronics",
        is_active=True
    )
    db_session.add(product)
    db_session.commit()
    db_session.refresh(product)
    
    # Make attributes accessible after session closes
    db_session.expunge(product)
    
    return product


@pytest.fixture
def auth_headers(client, test_user):
    """Get authentication headers for a regular user."""
    response = client.post(
        "/api/v1/auth/login",
        data={
            "username": "testuser",
            "password": "testpassword123"
        }
    )
    token = response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def admin_auth_headers(client, test_admin_user):
    """Get authentication headers for an admin user."""
    response = client.post(
        "/api/v1/auth/login",
        data={
            "username": "admin",
            "password": "adminpassword123"
        }
    )
    token = response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}
