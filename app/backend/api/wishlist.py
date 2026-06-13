from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import and_
from sqlalchemy.orm import Session
from typing import Annotated
from models.models import (
    Wishlist,
    Products
)

from utils.commonservices import getdb
from core.security import get_current_user


router = APIRouter(tags=["Wishlist"])


@router.post("/wishlist/add/{product_id}")
def add_to_wishlist(
    product_id: int,
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

    existing_item = db.query(Wishlist).filter(
        Wishlist.user_id == user.id,
        Wishlist.product_id == product_id,
        Wishlist.is_deleted == False
    ).first()

    if existing_item:
        raise HTTPException(
            status_code=409,
            detail="Product already in wishlist"
        )

    try:
        wishlist_item = Wishlist(
            user_id=user.id,
            product_id=product_id
        )

        db.add(wishlist_item)
        db.commit()
        db.refresh(wishlist_item)
        return {
            "wishlist_id": wishlist_item.id,
            "message": "Product added to wishlist"
        }
    except Exception:
        db.rollback()
        raise


@router.get("/wishlist")
def get_wishlist(
    db: Annotated[Session, Depends(getdb)],
    current_user=Depends(get_current_user)
):
    user = current_user

    wishlist_items = (
        db.query(Wishlist)
        .join(Products)
        .filter(
            Wishlist.user_id == user.id,
            Wishlist.is_deleted == False,
            Products.is_deleted == False
        )
        .all()
    )

    data = []

    for item in wishlist_items:
        data.append({
            "wishlist_id": item.id,
            "product_id": item.product.id,
            "product_name": item.product.name,
            "summary": item.product.summary,
            "cover_image": item.product.cover_img_path,
            "slug": item.product.slug
        })

    return {
        "count": len(data),
        "items": data
    }


@router.delete("/wishlist/product/{product_id}")
def remove_from_wishlist(
    product_id: int,
    db: Annotated[Session, Depends(getdb)],
    current_user=Depends(get_current_user)
):
    user = current_user

    wishlist_item = db.query(Wishlist).filter(
        Wishlist.user_id == user.id,
        Wishlist.product_id == product_id,
        Wishlist.is_deleted == False
    ).first()

    if not wishlist_item:
        raise HTTPException(
            status_code=404,
            detail="Wishlist item not found"
        )

    try:
        wishlist_item.is_deleted = True

        db.commit()
        return {
            "message": "Product removed from wishlist"
        }
    except Exception:
        db.rollback()
        raise


@router.get("/wishlist/check/{product_id}")
def check_wishlist_status(
    product_id: int,
    db: Annotated[Session, Depends(getdb)],
    current_user=Depends(get_current_user)
):
    user = current_user

    item = db.query(Wishlist).filter(
        Wishlist.user_id == user.id,
        Wishlist.product_id == product_id,
        Wishlist.is_deleted == False
    ).first()

    return {
        "is_in_wishlist": item is not None
    }


@router.get("/wishlist/count")
def wishlist_count(
    db: Annotated[Session, Depends(getdb)],
    current_user=Depends(get_current_user)
):
    user = current_user

    count = db.query(Wishlist).filter(
        Wishlist.user_id == user.id,
        Wishlist.is_deleted == False
    ).count()

    return {
        "count": count
    }