from sqlalchemy.orm import Session
from fastapi import HTTPException, status
from app.models.order import Order, OrderItem
from app.models.product import Product
from app.schemas.order import OrderCreate

def create_order(db: Session, order_data: OrderCreate, user_id: int):
    """
    Business logic for creating an order. 
    Includes stock validation and price snapshots.
    """
    total_amount = 0.0
    order_items_data = []
    
    for item in order_data.items:
        product = db.query(Product).filter(Product.id == item.product_id).first()
        
        if not product:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Product with id {item.product_id} not found"
            )
        
        if product.stock_quantity < item.quantity:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Insufficient stock for product {product.name}"
            )
        
        item_total = product.price * item.quantity
        total_amount += item_total
        
        order_items_data.append({
            "product_id": product.id,
            "quantity": item.quantity,
            "price_at_purchase": product.price
        })
        
        # Update stock
        product.stock_quantity -= item.quantity
    
    # Create order record
    new_order = Order(user_id=user_id, total_amount=total_amount)
    db.add(new_order)
    db.flush()  # Get ID
    
    for item_data in order_items_data:
        db.add(OrderItem(order_id=new_order.id, **item_data))
    
    db.commit()
    db.refresh(new_order)
    return new_order
