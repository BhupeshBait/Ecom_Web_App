from typing import Annotated
from fastapi import APIRouter, Depends, HTTPException

from sqlalchemy import and_
from sqlalchemy.orm import Session
import uuid
from models.models import (Addresses, Cart, Cart_Item,
                           Product_Stock, Products,Orders, Order_Items, Payments,OrderStatus)
from schemas.schemas import (order_create_inputs, order_status_update_inputs, order_cancel_inputs)
from utils.commonservices import (getdb)
from core.security import (get_current_user,require_admin)



router = APIRouter(tags=["Orders"])


@router.post("/order/create")
def createOrder(db: Annotated[Session, Depends(getdb)], clsinput: order_create_inputs,
                current_user = Depends(get_current_user)):
    user = current_user
    
    address = db.query(Addresses).filter(
        and_(
            Addresses.id == clsinput.address_id,
            Addresses.user_id == user.id,
            Addresses.is_deleted == False
        )
    ).first()
    
    if not address:
        raise HTTPException(status_code=404, detail="Address not found")
    
    cart = db.query(Cart).filter(Cart.user_id == user.id).first()
    if not cart:
        raise HTTPException(status_code=404, 
                            detail="Cart is empty")
    
    cart_items = db.query(Cart_Item).filter(
        and_(
            Cart_Item.cart_id == cart.id,
            Cart_Item.is_deleted == False
        )
    ).all()
    
    if not cart_items:
        raise HTTPException(
            status_code=400,
            detail="No items in cart"
        )
    
    for item in cart_items:
        stock = db.query(Product_Stock).filter(
            Product_Stock.id == item.product_stock_id
        ).first()
        if not stock or stock.quantity < item.quantity:
            raise HTTPException(
                status_code=409,
                detail=f"Insufficient stock for product {item.product.name}"
            )
    
    order_number = f"ORD-{uuid.uuid4().hex[:10].upper()}"
    total_amount = cart.total
    
    order = Orders(
        user_id=user.id,
        order_number=order_number,
        status=OrderStatus.PENDING,
        total_amount=total_amount,
        final_amount=total_amount,
        shipping_address_id=address.id
    )
    
    try:
        db.add(order)
        db.flush()
    
        for cart_item in cart_items:
            order_item = Order_Items(
                user_id=user.id,
                order_id=order.id,
                product_id=cart_item.product_id,
                product_stock_id=cart_item.product_stock_id,
                quantity=cart_item.quantity,
                price=cart_item.productStock.price,
                total_price=cart_item.quantity * cart_item.productStock.price
            )
            
            db.add(order_item)
            
            stock = db.query(Product_Stock).filter(
                Product_Stock.id == cart_item.product_stock_id
            ).first()
            stock.quantity -= cart_item.quantity
            cart_item.is_deleted = True
        
            cart.total = 0
            db.commit()
            db.refresh(order)
            return {
                "order_id": order.id,
                "order_number": order.order_number,
                "status": order.status,
                "total_amount": order.total_amount,
                "message": "Order created successfully"
            }
    except Exception:
        db.rollback()
        raise


@router.get("/order/list")
def getUserOrders(db: Annotated[Session, Depends(getdb)], skip: int = 0, limit: int = 10,
                  current_user = Depends(get_current_user)):
    user = current_user
    
    orders = db.query(Orders).filter(
        and_(
            Orders.user_id == user.id,
            Orders.is_deleted == False
        )
    ).order_by(Orders.created_at.desc()).offset(skip).limit(limit).all()
    
    order_list = []
    for order in orders:
        order_list.append({
            "order_id": order.id,
            "order_number": order.order_number,
            "order_date": order.created_at,
            "status": order.status,
            "total_amount": order.total_amount,
            "final_amount": order.final_amount
        })
    
    return {"orders": order_list, "total": len(order_list)}


@router.get("/order/{order_id}")
def getOrderDetails(order_id: int, db: Annotated[Session, Depends(getdb)],
                    current_user = Depends(get_current_user)):
    user = current_user
    
    order = db.query(Orders).filter(
        and_(
            Orders.id == order_id,
            Orders.user_id == user.id,
            Orders.is_deleted == False
        )
    ).first()
    
    if not order:
        raise HTTPException(status_code=404, 
                            detail="Order not found")
    
    order_items = db.query(Order_Items).filter(
        and_(
            Order_Items.order_id == order.id,
            Order_Items.is_deleted == False
        )
    ).all()
    
    items = []
    for item in order_items:
        product = db.query(Products).filter(Products.id == item.product_id).first()
        items.append({
            "product_id": item.product_id,
            "product_name": product.name if product else "Product",
            "quantity": item.quantity,
            "price": item.price,
            "total_price": item.total_price
        })
    
    address = db.query(Addresses).filter(Addresses.id == order.shipping_address_id).first()
    
    return {
        "order": {
            "order_id": order.id,
            "order_number": order.order_number,
            "order_date": order.created_at,
            "status": order.status,
            "total_amount": order.total_amount,
            "final_amount": order.final_amount,
            "shipping_charge": order.shipping_charge,
            "tax_amount": order.tax_amount,
            "discount_amount": order.discount_amount,
            "delivery_address": {
                "street": address.street if address else "",
                "city": address.city if address else "",
                "state": address.state if address else "",
                "postal_code": address.postal_code if address else ""
            },
            "items": items
        }
    }


@router.put("/order/{order_id}/status")
def updateOrderStatus(order_id: int, db: Annotated[Session, Depends(getdb)],
                      clsinput: order_status_update_inputs,
                      current_user = Depends(require_admin)):
    user = current_user
    
    order = db.query(Orders).filter(
        and_(
            Orders.id == order_id,
            Orders.is_deleted == False
        )
    ).first()
    
    if not order:
        raise HTTPException(status_code=404, 
                            detail="Order not found")
    
    valid_statuses = [
        OrderStatus.PENDING,
        OrderStatus.PROCESSING,
        OrderStatus.SHIPPED,
        OrderStatus.DELIVERED,
        OrderStatus.CANCELED
    ]
    if clsinput.status not in valid_statuses:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid status. Valid statuses are: {', '.join(valid_statuses)}"
        )
    
    order.status = OrderStatus(
        clsinput.status.lower()
    )
    
    if clsinput.tracking_number:
        payment = db.query(Payments).filter(Payments.order_id == order.id).first()
        if not payment:
            payment = Payments(
                order_id=order.id,
                payment_method=clsinput.tracking_number,
                amount=order.total_amount,
                status=OrderStatus.INITIATED
            )
            db.add(payment)
    
    try:
        db.commit()
        db.refresh(order)
        return {
            "order_id": order.id,
            "status": order.status,
            "status_updated_at": order.updated_at,
            "message": "Order status updated successfully"
        }
    except Exception:
        db.rollback()
        raise


@router.put("/order/{order_id}/cancel")
def cancelOrder(order_id: int, db: Annotated[Session, Depends(getdb)],
                 clsinput: order_cancel_inputs,
                 current_user = Depends(get_current_user)):
    user = current_user
    
    order = db.query(Orders).filter(
        and_(
            Orders.id == order_id,
            Orders.user_id == user.id,
            Orders.is_deleted == False
        )
    ).first()
    
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    
    if order.status not in ["PENDING", "PROCESSING"]:
        raise HTTPException(
            status_code=400,
            detail=f"Cannot cancel order with status {order.status}"
        )
    
    order_items = db.query(Order_Items).filter(
        and_(
            Order_Items.order_id == order.id,
            Order_Items.is_deleted == False
        )
    ).all()
    
    for item in order_items:
        stock = db.query(Product_Stock).filter(
            Product_Stock.id == item.product_stock_id
        ).first()
        if stock:
            stock.quantity += item.quantity
    
    order.status =  OrderStatus.CANCELED
    order.reason=clsinput.reason
    
    try:
        db.commit()
        db.refresh(order)
        return {
            "order_id": order.id,
            "status": order.status,
            "cancelled_at": order.updated_at,
            "refund_amount": order.total_amount,
            "refund_status": "pending",
            "message": "Order cancelled successfully. Refund will be processed in 3-5 business days"
        }
    except Exception:
        db.rollback()
        raise

@router.get("/order/get/{status}")
def get_order_with_status(status: str, db: Annotated[Session, Depends(getdb)],
                          current_user = Depends(get_current_user)):
    user = current_user
    valid_statuses = [
        "pending",
        "processing",
        "shipped",
        "delivered",
        "canceled"
    ]

    if status.lower() not in valid_statuses:
        raise HTTPException(
            status_code=400,
            detail="Invalid order status"
        )
    order = db.query(Orders).filter(
        and_(
            Orders.status==status,
            Orders.user_id == user.id,
            Orders.is_deleted == False
        )
    ).all()

    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    
    return{"Orders":order}
    