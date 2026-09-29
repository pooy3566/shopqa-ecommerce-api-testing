import pytest
from fastapi import status


def test_create_order(client, auth_headers, test_product):
    """Test creating a new order."""
    order_data = {
        "items": [
            {
                "product_id": test_product.id,
                "quantity": 2
            }
        ]
    }
    
    response = client.post(
        "/api/v1/orders/",
        json=order_data,
        headers=auth_headers
    )
    
    assert response.status_code == status.HTTP_201_CREATED
    data = response.json()
    assert "id" in data
    assert data["total_amount"] == test_product.price * 2
    assert len(data["items"]) == 1


def test_create_order_insufficient_stock(client, auth_headers, test_product):
    """Test creating an order with insufficient stock."""
    order_data = {
        "items": [
            {
                "product_id": test_product.id,
                "quantity": 1000  # More than available stock
            }
        ]
    }
    
    response = client.post(
        "/api/v1/orders/",
        json=order_data,
        headers=auth_headers
    )
    
    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert "Insufficient stock" in response.json()["detail"]


def test_create_order_nonexistent_product(client, auth_headers):
    """Test creating an order with a non-existent product."""
    order_data = {
        "items": [
            {
                "product_id": 9999,
                "quantity": 1
            }
        ]
    }
    
    response = client.post(
        "/api/v1/orders/",
        json=order_data,
        headers=auth_headers
    )
    
    assert response.status_code == status.HTTP_404_NOT_FOUND


def test_list_user_orders(client, auth_headers, test_product):
    """Test listing orders for the authenticated user."""
    # Create an order first
    order_data = {
        "items": [
            {
                "product_id": test_product.id,
                "quantity": 1
            }
        ]
    }
    client.post("/api/v1/orders/", json=order_data, headers=auth_headers)
    
    # List orders
    response = client.get("/api/v1/orders/", headers=auth_headers)
    
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert isinstance(data, list)
    assert len(data) >= 1


def test_get_order_by_id(client, auth_headers, test_product):
    """Test getting a specific order by ID."""
    # Create an order first
    order_data = {
        "items": [
            {
                "product_id": test_product.id,
                "quantity": 1
            }
        ]
    }
    create_response = client.post(
        "/api/v1/orders/",
        json=order_data,
        headers=auth_headers
    )
    order_id = create_response.json()["id"]
    
    # Get the order
    response = client.get(f"/api/v1/orders/{order_id}", headers=auth_headers)
    
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert data["id"] == order_id


def test_get_order_summary(client, auth_headers, test_product):
    """Test getting order summary with raw SQL."""
    # Create an order first
    order_data = {
        "items": [
            {
                "product_id": test_product.id,
                "quantity": 1
            }
        ]
    }
    client.post("/api/v1/orders/", json=order_data, headers=auth_headers)
    
    # Get order summary
    response = client.get("/api/v1/orders/summary", headers=auth_headers)
    
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert isinstance(data, list)
    assert len(data) >= 1
    assert "order_id" in data[0]
    assert "user_email" in data[0]
    assert "item_count" in data[0]
