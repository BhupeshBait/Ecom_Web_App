from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import and_, func
from sqlalchemy.orm import Session

from models.models import Reviews, Products
from schemas.reviewSchemas import (
    review_create_inputs,
    review_update_inputs
)
from utils.commonservices import getdb
from core.security import get_current_user


router = APIRouter(tags=["Reviews"])


@router.post("/reviews/{product_id}")
def create_review(
    product_id: int,
    clsinput: review_create_inputs,
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

    existing_review = db.query(Reviews).filter(
        and_(
            Reviews.user_id == user.id,
            Reviews.product_id == product_id,
            Reviews.is_deleted == False
        )
    ).first()

    if existing_review:
        raise HTTPException(
            status_code=409,
            detail="You already reviewed this product"
        )

    review = Reviews(
        user_id=user.id,
        product_id=product_id,
        rating=clsinput.rating,
        comment=clsinput.comment
    )

    try:
        db.add(review)
        db.commit()
        db.refresh(review)
        return {
            "message": "Review added successfully",
            "review_id": review.id
        }
    except Exception:
        db.rollback()
        raise


@router.get("/reviews/{product_id}")
def get_reviews(
    product_id: int,
    db: Annotated[Session, Depends(getdb)]
):
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

    reviews = db.query(Reviews).filter(
        and_(
            Reviews.product_id == product_id,
            Reviews.is_deleted == False
        )
    ).all()

    result = []

    for review in reviews:
        result.append(
            {
                "review_id": review.id,
                "user_id": review.user_id,
                "rating": review.rating,
                "comment": review.comment,
                "created_at": review.created_at
            }
        )

    return {
        "total_reviews": len(result),
        "reviews": result
    }


@router.put("/reviews/{review_id}")
def update_review(
    review_id: int,
    clsinput: review_update_inputs,
    db: Annotated[Session, Depends(getdb)],
    current_user=Depends(get_current_user)
):
    user = current_user

    review = db.query(Reviews).filter(
        and_(
            Reviews.id == review_id,
            Reviews.user_id == user.id,
            Reviews.is_deleted == False
        )
    ).first()

    if not review:
        raise HTTPException(
            status_code=404,
            detail="Review not found"
        )

    if clsinput.rating is not None:
        review.rating = clsinput.rating

    if clsinput.comment is not None:
        review.comment = clsinput.comment

    try:
        db.commit()
        db.refresh(review)
        return {
            "message": "Review updated successfully"
        }
    except Exception:
        db.rollback()
        raise


@router.delete("/reviews/{review_id}")
def delete_review(
    review_id: int,
    db: Annotated[Session, Depends(getdb)],
    current_user=Depends(get_current_user)
):
    user = current_user

    review = db.query(Reviews).filter(
        and_(
            Reviews.id == review_id,
            Reviews.user_id == user.id,
            Reviews.is_deleted == False
        )
    ).first()

    if not review:
        raise HTTPException(
            status_code=404,
            detail="Review not found"
        )

    try:
        review.is_deleted = True

        db.commit()
        return {
            "message": "Review deleted successfully"
        }
    except Exception:
        db.rollback()
        raise


@router.get("/reviews/product/{product_id}/rating")
def get_product_rating(
    product_id: int,
    db: Annotated[Session, Depends(getdb)]
):
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

    average_rating = db.query(
        func.avg(Reviews.rating)
    ).filter(
        and_(
            Reviews.product_id == product_id,
            Reviews.is_deleted == False
        )
    ).scalar()

    total_reviews = db.query(
        Reviews
    ).filter(
        and_(
            Reviews.product_id == product_id,
            Reviews.is_deleted == False
        )
    ).count()

    return {
        "product_id": product_id,
        "average_rating": round(float(average_rating or 0), 1),
        "total_reviews": total_reviews
    }