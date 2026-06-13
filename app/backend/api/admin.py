from typing import Annotated
from models.models import (Users, Products, Orders, Payments, Product_Stock,OrderStatus)
from utils.commonservices import getdb
from core.security import require_admin
from sqlalchemy import func
from fastapi import APIRouter, Depends, HTTPException   
from sqlalchemy.orm import Session


router = APIRouter(tags=["Admin"])


@router.get("/admin/dashboard")
def dashboard(
    db: Annotated[Session, Depends(getdb)],
    current_user=Depends(require_admin)
):
    total_users = db.query(Users).filter(
        Users.is_deleted == False
    ).count()

    total_products = db.query(Products).filter(
        Products.is_deleted == False
    ).count()

    total_orders = db.query(Orders).filter(
        Orders.is_deleted == False
    ).count()

    total_revenue = db.query(
        func.coalesce(
            func.sum(Orders.final_amount),
            0
        )
    ).filter(
        Orders.status == OrderStatus.DELIVERED
    ).scalar()

    pending_orders = db.query(Orders).filter(
        Orders.status == OrderStatus.PENDING,
        Orders.is_deleted == False
    ).count()

    low_stock = db.query(Product_Stock).filter(
        Product_Stock.quantity <= 5,
        Product_Stock.is_deleted == False
    ).count()

    return {
        "total_users": total_users,
        "total_products": total_products,
        "total_orders": total_orders,
        "total_revenue": total_revenue,
        "pending_orders": pending_orders,
        "low_stock_products": low_stock
    }


@router.get("/admin/users")
def get_all_users(
    db: Annotated[Session, Depends(getdb)],
    current_user=Depends(require_admin)
):
    users = db.query(Users).filter(
        Users.is_deleted == False
    ).all()

    return {
        "count": len(users),
        "users": users
    }


@router.get("/admin/users/{user_id}")
def get_user(
    user_id: int,
    db: Annotated[Session, Depends(getdb)],
    current_user=Depends(require_admin)
):
    user = db.query(Users).filter(
        Users.id == user_id,
        Users.is_deleted == False
    ).first()

    if not user:
        raise HTTPException(
            status_code=404,
            detail="User not found"
        )

    return user

@router.delete("/admin/users/{user_id}")
def delete_user(
    user_id: int,
    db: Annotated[Session, Depends(getdb)],
    current_user=Depends(require_admin)
):
    user = db.query(Users).filter(
        Users.id == user_id,
        Users.is_deleted == False
    ).first()

    if not user:
        raise HTTPException(
            status_code=404,
            detail="User not found"
        )

    try:
        user.is_deleted = True

        db.commit()
        return {
            "message": "User deleted successfully"
        }
    except Exception:
        db.rollback()
        raise


@router.get("/admin/orders")
def get_all_orders(
    db: Annotated[Session, Depends(getdb)],
    current_user=Depends(require_admin)
):
    orders = db.query(Orders).filter(
        Orders.is_deleted == False
    ).order_by(
        Orders.created_at.desc()
    ).all()

    return {
        "count": len(orders),
        "orders": orders
    }


@router.get("/admin/orders/{order_id}")
def get_order(
    order_id: int,
    db: Annotated[Session, Depends(getdb)],
    current_user=Depends(require_admin)
):
    order = db.query(Orders).filter(
        Orders.id == order_id,
        Orders.is_deleted == False
    ).first()

    if not order:
        raise HTTPException(
            status_code=404,
            detail="Order not found"
        )

    return order


@router.get("/admin/payments")
def get_payments(
    db: Annotated[Session, Depends(getdb)],
    current_user=Depends(require_admin)
):
    payments = db.query(Payments).filter(
        Payments.is_deleted == False
    ).all()

    return {
        "count": len(payments),
        "payments": payments
    }


@router.get("/admin/stock/low")
def low_stock_report(
    db: Annotated[Session, Depends(getdb)],
    current_user=Depends(require_admin)
):
    stocks = db.query(Product_Stock).filter(
        Product_Stock.quantity <= 5,
        Product_Stock.is_deleted == False
    ).all()

    return {
        "count": len(stocks),
        "items": stocks
    }


@router.get("/admin/stock/out-of-stock")
def out_of_stock_report(
    db: Annotated[Session, Depends(getdb)],
    current_user=Depends(require_admin)
):
    stocks = db.query(Product_Stock).filter(
        Product_Stock.quantity == 0,
        Product_Stock.is_deleted == False
    ).all()

    return {
        "count": len(stocks),
        "items": stocks
    }