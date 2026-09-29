from pydantic import BaseModel, Field, ConfigDict
from typing import List, Optional
from datetime import datetime
from app.models.order import OrderStatus


class OrderItemCreate(BaseModel):
    """Schema for creating an order item."""
    product_id: int = Field(..., gt=0)
    quantity: int = Field(..., gt=0)


class OrderItemResponse(BaseModel):
    """Schema for order item response."""
    id: int
    product_id: int
    quantity: int
    price_at_purchase: float
    
    model_config = ConfigDict(from_attributes=True)


class OrderCreate(BaseModel):
    """Schema for creating a new order."""
    items: List[OrderItemCreate] = Field(..., min_length=1)


class OrderResponse(BaseModel):
    """Schema for order response."""
    id: int
    user_id: int
    total_amount: float
    status: OrderStatus
    created_at: datetime
    updated_at: Optional[datetime] = None
    items: List[OrderItemResponse] = []
    
    model_config = ConfigDict(from_attributes=True)


class OrderSummary(BaseModel):
    """Schema for order summary (from raw SQL queries)."""
    order_id: int
    user_email: str
    total_amount: float
    item_count: int
    status: str
    created_at: datetime
