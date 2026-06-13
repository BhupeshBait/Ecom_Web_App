from typing import Annotated

from fastapi import (
    APIRouter,
    Depends,
    HTTPException
)

from sqlalchemy.orm import Session
from sqlalchemy import and_

from models.models import (
    Product_Stock,
    Products
)

from schemas.schemas import (
    stock_inputs,
    stock_update_inputs
)

from utils.commonservices import getdb

from core.security import require_admin
from utils.logger import logger


router = APIRouter(tags=["Stock"])


def serialize_stock(stock):
    return {
        "id": stock.id,
        "product_id": stock.product_id,
        "sku_id": stock.sku_id,
        "price": stock.price,
        "quantity": stock.quantity
    }



@router.post("/stock")
def add_stock(
    clsinput: stock_inputs,
    db: Annotated[Session, Depends(getdb)],
    current_user=Depends(require_admin)
):
    product = db.query(Products).filter(
        Products.id == clsinput.product_id,
        Products.is_deleted == False
    ).first()

    if not product:
        raise HTTPException(
            status_code=404,
            detail="Product not found"
        )

    existing_sku = db.query(Product_Stock).filter(
        Product_Stock.sku_id == clsinput.sku_id
    ).first()

    if existing_sku:
        raise HTTPException(
            status_code=409,
            detail="SKU already exists"
        )

    try:
        stock = Product_Stock(
            product_id=clsinput.product_id,
            sku_id=clsinput.sku_id,
            price=clsinput.price,
            quantity=clsinput.quantity
        )

        db.add(stock)
        db.commit()
        db.refresh(stock)
        logger.info(f"stock.create: product_id={stock.product_id} sku={stock.sku_id} user_id={current_user.id}")
        return {
            "message": "Stock created",
            "data": serialize_stock(stock)
        }
    except Exception:
        db.rollback()
        raise


@router.get("/stock/product/{product_id}")
def get_product_stock(
    product_id: int,
    db: Annotated[Session, Depends(getdb)],
    current_user=Depends(require_admin)
):
    stocks = db.query(Product_Stock).filter(
        Product_Stock.product_id == product_id,
        Product_Stock.is_deleted == False
    ).all()

    return {
        "data": [
            serialize_stock(stock)
            for stock in stocks
        ]
    }


@router.put("/stock/{id}")
def update_stock(
    id: int,
    clsinput: stock_update_inputs,
    db: Annotated[Session, Depends(getdb)],
    current_user=Depends(require_admin)
):
    stock = db.query(Product_Stock).filter(
        Product_Stock.id == id,
        Product_Stock.is_deleted == False
    ).first()

    if not stock:
        raise HTTPException(
            status_code=404,
            detail="Stock not found"
        )

    if clsinput.sku_id is not None:
        duplicate = db.query(Product_Stock).filter(
            Product_Stock.sku_id == clsinput.sku_id,
            Product_Stock.id != id
        ).first()

        if duplicate:
            raise HTTPException(
                status_code=409,
                detail="SKU already exists"
            )

        stock.sku_id = clsinput.sku_id

    if clsinput.price is not None:
        stock.price = clsinput.price

    if clsinput.quantity is not None:
        stock.quantity = clsinput.quantity

    try:
        db.commit()
        db.refresh(stock)
        logger.info(f"stock.update: stock_id={stock.id} user_id={current_user.id}")
        return {
            "message": "Stock updated",
            "data": serialize_stock(stock)
        }
    except Exception:
        db.rollback()
        raise


@router.delete("/stock/{id}")
def delete_stock(
    id: int,
    db: Annotated[Session, Depends(getdb)],
    current_user=Depends(require_admin)
):
    stock = db.query(Product_Stock).filter(
        Product_Stock.id == id,
        Product_Stock.is_deleted == False
    ).first()

    if not stock:
        raise HTTPException(
            status_code=404,
            detail="Stock not found"
        )

    try:
        stock.is_deleted = True

        db.commit()
        logger.info(f"stock.delete: stock_id={stock.id} user_id={current_user.id}")
        return {
            "message": "Stock deleted"
        }
    except Exception:
        db.rollback()
        raise