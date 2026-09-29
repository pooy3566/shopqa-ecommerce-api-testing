import pytest
from fastapi import status


def test_create_product_as_admin(client, admin_auth_headers):
    """Test product creation by admin user."""
    product_data = {
        "name": "New Product",
        "description": "A new product",
        "price": 49.99,
        "stock_quantity": 50,
        "category": "Books",
        "is_active": True
    }
    
    response = client.post(
        "/api/v1/products/",
        json=product_data,
        headers=admin_auth_headers
    )
    
    assert response.status_code == status.HTTP_201_CREATED
    data = response.json()
    assert data["name"] == product_data["name"]
    assert data["price"] == product_data["price"]
    assert "id" in data


def test_create_product_as_regular_user(client, auth_headers):
    """Test that regular users cannot create products."""
    product_data = {
        "name": "New Product",
        "description": "A new product",
        "price": 49.99,
        "stock_quantity": 50,
        "category": "Books"
    }
    
    response = client.post(
        "/api/v1/products/",
        json=product_data,
        headers=auth_headers
    )
    
    assert response.status_code == status.HTTP_403_FORBIDDEN


def test_create_product_invalid_price(client, admin_auth_headers):
    """Test product creation with invalid price."""
    product_data = {
        "name": "Invalid Product",
        "description": "Product with negative price",
        "price": -10.00,
        "stock_quantity": 10
    }
    
    response = client.post(
        "/api/v1/products/",
        json=product_data,
        headers=admin_auth_headers
    )
    
    assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY


def test_list_products(client, auth_headers, test_product):
    """Test listing all products."""
    response = client.get("/api/v1/products/", headers=auth_headers)
    
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert isinstance(data, list)
    assert len(data) >= 1


def test_get_product_by_id(client, auth_headers, test_product):
    """Test getting a specific product."""
    response = client.get(
        f"/api/v1/products/{test_product.id}",
        headers=auth_headers
    )
    
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert data["id"] == test_product.id
    assert data["name"] == test_product.name


def test_get_nonexistent_product(client, auth_headers):
    """Test getting a product that doesn't exist."""
    response = client.get("/api/v1/products/9999", headers=auth_headers)
    
    assert response.status_code == status.HTTP_404_NOT_FOUND


def test_update_product_as_admin(client, admin_auth_headers, test_product):
    """Test updating a product as admin."""
    update_data = {
        "name": "Updated Product Name",
        "price": 129.99
    }
    
    response = client.put(
        f"/api/v1/products/{test_product.id}",
        json=update_data,
        headers=admin_auth_headers
    )
    
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert data["name"] == update_data["name"]
    assert data["price"] == update_data["price"]


def test_delete_product_as_admin(client, admin_auth_headers, test_product):
    """Test deleting a product as admin."""
    response = client.delete(
        f"/api/v1/products/{test_product.id}",
        headers=admin_auth_headers
    )
    
    assert response.status_code == status.HTTP_204_NO_CONTENT
    
    # Verify product is deleted
    get_response = client.get(
        f"/api/v1/products/{test_product.id}",
        headers=admin_auth_headers
    )
    assert get_response.status_code == status.HTTP_404_NOT_FOUND
