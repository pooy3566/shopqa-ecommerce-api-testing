"""补充订单业务边界测试。

这些用例专门验证数量边界和库存扣减，便于回归时快速定位业务风险。
"""

from fastapi import status
import pytest

from app.models.product import Product
from tests.conftest import TestingSessionLocal


@pytest.mark.integration
def test_create_order_rejects_zero_quantity(client, auth_headers, test_product):
    """数量为 0 不属于有效订单项，应在请求校验阶段被拒绝。"""
    response = client.post(
        "/api/v1/orders/",
        json={"items": [{"product_id": test_product.id, "quantity": 0}]},
        headers=auth_headers,
    )

    assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY


@pytest.mark.integration
def test_create_order_decrements_inventory(client, auth_headers, test_product):
    """成功下单后，库存应按订单数量扣减。"""
    original_stock = test_product.stock_quantity
    response = client.post(
        "/api/v1/orders/",
        json={"items": [{"product_id": test_product.id, "quantity": 3}]},
        headers=auth_headers,
    )

    assert response.status_code == status.HTTP_201_CREATED
    # 请求 fixture 会在响应后关闭共享会话，因此用独立会话读取提交后的真实库存。
    verification_session = TestingSessionLocal()
    try:
        saved_product = verification_session.query(Product).filter(Product.id == test_product.id).one()
        assert saved_product.stock_quantity == original_stock - 3
    finally:
        verification_session.close()
