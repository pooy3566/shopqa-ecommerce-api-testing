import pytest
from fastapi import status


def test_register_user(client):
    """Test user registration."""
    response = client.post(
        "/api/v1/auth/register",
        json={
            "email": "newuser@example.com",
            "username": "newuser",
            "password": "securepassword123",
            "full_name": "New User"
        }
    )
    
    assert response.status_code == status.HTTP_201_CREATED
    data = response.json()
    assert data["email"] == "newuser@example.com"
    assert data["username"] == "newuser"
    assert "hashed_password" not in data
    assert data["is_active"] is True
    assert data["is_admin"] is False


def test_register_duplicate_user(client, test_user):
    """Test registration with existing email/username."""
    response = client.post(
        "/api/v1/auth/register",
        json={
            "email": "test@example.com",
            "username": "testuser",
            "password": "password123",
            "full_name": "Duplicate User"
        }
    )
    
    # Generic response: registration must not confirm which account exists (CWE-204).
    assert response.status_code == status.HTTP_409_CONFLICT
    assert "already registered" not in response.json()["detail"]


def test_login_success(client, test_user):
    """Test successful login."""
    response = client.post(
        "/api/v1/auth/login",
        data={
            "username": "testuser",
            "password": "testpassword123"
        }
    )
    
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"


def test_login_wrong_password(client, test_user):
    """Test login with incorrect password."""
    response = client.post(
        "/api/v1/auth/login",
        data={
            "username": "testuser",
            "password": "wrongpassword"
        }
    )
    
    assert response.status_code == status.HTTP_401_UNAUTHORIZED


def test_login_nonexistent_user(client):
    """Test login with non-existent user."""
    response = client.post(
        "/api/v1/auth/login",
        data={
            "username": "nonexistent",
            "password": "password123"
        }
    )
    
    assert response.status_code == status.HTTP_401_UNAUTHORIZED


def test_access_protected_endpoint_without_token(client):
    """Test accessing protected endpoint without authentication."""
    response = client.get("/api/v1/products/")
    
    assert response.status_code == status.HTTP_401_UNAUTHORIZED


def test_access_protected_endpoint_with_token(client, auth_headers, test_product):
    """Test accessing protected endpoint with valid token."""
    response = client.get("/api/v1/products/", headers=auth_headers)
    
    assert response.status_code == status.HTTP_200_OK
