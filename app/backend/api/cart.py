from typing import Annotated
from fastapi import APIRouter, Depends, Form, HTTPException
from sqlalchemy import and_
from sqlalchemy.orm import Session
from models.models import ( Cart, Cart_Item,Product_Stock, Products)
from schemas.cartSchemas import (addToCartInputs)
from utils.commonservices import  getdb
from core.security import (get_current_user)

router = APIRouter(tags=["Cart"])


@router.post("/cart/add/{product_id}")
def addToCart(
    product_id: int,
    clsinput: addToCartInputs,
    db: Annotated[Session, Depends(getdb)],
    current_user=Depends(get_current_user)
):
    user = current_user

    product = db.query(Products).filter(
        and_(
            Products.id == product_id,
            Products.is_deleted == False
        )
    ).first()

    if not product:
        raise HTTPException(
            status_code=404,
            detail="Product not found"
        )

    product_stock = db.query(Product_Stock).filter(
        and_(
            Product_Stock.product_id == product_id,
            Product_Stock.is_deleted == False
        )
    ).first()

    if not product_stock:
        raise HTTPException(
            status_code=404,
            detail="Product stock not found"
        )

    if clsinput.quantity > product_stock.quantity:
        raise HTTPException(
            status_code=409,
            detail="Insufficient stock"
        )

    cart = db.query(Cart).filter(
        Cart.user_id == user.id
    ).first()

    try:
        if not cart:
            cart = Cart(
                user_id=user.id,
                total=0
            )
            db.add(cart)
            db.commit()
            db.refresh(cart)

        existing_item = db.query(Cart_Item).filter(
        Cart_Item.cart_id == cart.id,
        Cart_Item.product_id == product.id,
        Cart_Item.is_deleted == False
        ).first()

        if existing_item:

            new_quantity = (
                existing_item.quantity +
                clsinput.quantity
            )

            if new_quantity > product_stock.quantity:
                raise HTTPException(
                    status_code=409,
                    detail="Insufficient stock"
                )

            existing_item.quantity = new_quantity

        else:

            cart_item = Cart_Item(
                cart_id=cart.id,
                product_id=product.id,
                product_stock_id=product_stock.id,
                quantity=clsinput.quantity
            )

            db.add(cart_item)

        items = db.query(Cart_Item).filter(
            and_(
                Cart_Item.cart_id == cart.id,
                Cart_Item.is_deleted == False
            )
        ).all()

        cart.total = sum(
            item.quantity *
            item.productStock.price
            for item in items
        )

        db.commit()

        return {
                "message": "Product added to cart successfully",
                "cart_total": cart.total
            }
    
    except Exception as e:
        db.rollback()
        raise


@router.get('/cart/get')
def getCart(db: Annotated[Session, Depends(getdb)], current_user = Depends(get_current_user)):
    user = current_user
    cart = db.query(Cart).filter(Cart.user_id == user.id).first()
    if not cart:
        return {
            "items": [],
            "total": 0
        }
    cart_Items = db.query(Cart_Item).filter(
        and_(
            Cart_Item.is_deleted == False,
            Cart_Item.cart_id == cart.id)).all()
    return {"items": cart_Items,
            "total":cart.total}


@router.put('/cart/update/{cart_item_id}')
def cartUpdate(cart_item_id: int,
               db: Annotated[Session, Depends(getdb)], quantity: int = Form(...),
               current_user = Depends(get_current_user)):
    user = current_user
    cart_item = db.query(Cart_Item).join(Cart).filter(
        Cart_Item.id == cart_item_id,
        Cart.user_id == user.id).first()
    if not cart_item:
        raise HTTPException(status_code=404, detail="Item not found")
    if quantity > cart_item.productStock.quantity:
        raise HTTPException(status_code=409, detail="Insufficient Stock")
    cart_item.quantity = quantity
    cart = cart_item.cart
    items = db.query(Cart_Item).filter(
        and_(
            Cart_Item.cart_id == cart.id,
            Cart_Item.is_deleted == False)).all()
    cart.total = sum(
        item.quantity *
        item.productStock.price for item in items)
    try:
        db.commit()
        return {"message": "Cart updated",
                "cart_total": cart.total}
    except Exception:
        db.rollback()
        raise

@router.put("/CartItem/remove/{cart_item_id}")
def removeItem(cart_item_id: int,
               db: Annotated[Session, Depends(getdb)],
               current_user = Depends(get_current_user)):
    user = current_user
    cart = db.query(Cart).filter(Cart.user_id == user.id).first() 
    cart_item = db.query(Cart_Item).join(Cart).filter(
        Cart_Item.id == cart_item_id,
        Cart.user_id == user.id).first()
    if not cart_item:
        raise HTTPException(status_code=404, detail="Item not found")
    cart_item.is_deleted=True
    
    items = db.query(Cart_Item).filter(
        and_(
            Cart_Item.cart_id == cart.id,
            Cart_Item.is_deleted == False
        )
    ).all()

    cart.total = sum(
        item.quantity *
        item.productStock.price
        for item in items
    )
    try:
        db.commit()
        return {'Msg':"Item removed"}
    except Exception:
        db.rollback()
        raise

@router.put("/cart/clear")
def clearCart(db: Annotated[Session, Depends(getdb)], current_user = Depends(get_current_user)):
    user = current_user
    cart = db.query(Cart).filter(Cart.user_id == user.id).first()    
    if not cart:
        return {"message":"Cart not found"}    
    cart_Items = db.query(Cart_Item).filter(
        and_(
            Cart_Item.is_deleted == False,
            Cart_Item.cart_id == cart.id)).all()
    for cart_item in cart_Items:
        cart_item.is_deleted=True
    cart.total=0
    try:
        db.commit()
        return {"message":"Cart cleared!"}
    except Exception:
        db.rollback()
        raise