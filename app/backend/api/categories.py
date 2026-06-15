from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException

from sqlalchemy.orm import Session

from models.models import Categories, Sub_Categories , Products

from schemas.categorySchmas import (
    categoryInputs,
    SubcategoryInputs,
    categoryUpdateInputs,
    subcategoryUpdateInputs
)

from utils.commonservices import getdb
from core.security import require_admin



router = APIRouter(tags=["Categories"])


@router.post("/categories")
def create_category(
    clsinput: categoryInputs,
    db: Annotated[Session, Depends(getdb)],
    current_user=Depends(require_admin)
):
    exists = db.query(Categories).filter(
        Categories.name == clsinput.name,
        Categories.is_deleted == False
    ).first()

    if exists:
        raise HTTPException(
            status_code=409,
            detail="Category already exists"
        )

    category = Categories(
        name=clsinput.name,
        description=clsinput.description,
        slug=clsinput.slug
    )

    try:
        db.add(category)
        db.commit()
        db.refresh(category)
        return {
            "message": "Category created",
            "id": category.id
        }
    except Exception:
        db.rollback()
        raise


@router.post("/subcategories")
def create_subcategory(
    clsinput: SubcategoryInputs,
    db: Annotated[Session, Depends(getdb)],
    current_user=Depends(require_admin)
):
    category = db.query(Categories).filter(
        Categories.name == clsinput.parentName,
        Categories.is_deleted == False
    ).first()

    if not category:
        raise HTTPException(
            status_code=404,
            detail="Category not found"
        )

    exists = db.query(Sub_Categories).filter(
        Sub_Categories.name == clsinput.name,
        Sub_Categories.is_deleted == False
    ).first()

    if exists:
        raise HTTPException(
            status_code=409,
            detail="Subcategory already exists"
        )

    subcategory = Sub_Categories(
        name=clsinput.name,
        description=clsinput.description,
        parent_id=category.id,
        slug=clsinput.slug
    )

    try:
        db.add(subcategory)
        db.commit()
        db.refresh(subcategory)
        return {
            "message": "Subcategory created",
            "id": subcategory.id
        }
    except Exception:
        db.rollback()
        raise


@router.get("/categories")
def get_categories(
    db: Annotated[Session, Depends(getdb)]
):
    categories = db.query(Categories).filter(
        Categories.is_deleted == False
    ).all()

    return {
        "data": [
            {
                "id": category.id,
                "name": category.name,
                "description": category.description,
                "slug": category.slug
            }
            for category in categories
        ]
    }


@router.get("/categories/{id}")
def get_category(
    id: int,
    db: Annotated[Session, Depends(getdb)]
):
    category = db.query(Categories).filter(
        Categories.id == id,
        Categories.is_deleted == False
    ).first()

    if not category:
        raise HTTPException(
            status_code=404,
            detail="Category not found"
        )

    return {
        "id": category.id,
        "name": category.name,
        "description": category.description,
        "slug": category.slug
    }


@router.get("/categories/{id}/subcategories")
def get_category_subcategories(
    id: int,
    db: Annotated[Session, Depends(getdb)]
):
    category = db.query(Categories).filter(
        Categories.id == id,
        Categories.is_deleted == False
    ).first()

    if not category:
        raise HTTPException(
            status_code=404,
            detail="Category not found"
        )

    subcategories = db.query(Sub_Categories).filter(
        Sub_Categories.parent_id == id,
        Sub_Categories.is_deleted == False
    ).all()

    return {
        "data": [
            {
                "id": sub.id,
                "name": sub.name,
                "description": sub.description,
                "slug": sub.slug
            }
            for sub in subcategories
        ]
    }


@router.put("/categories/{id}")
def update_category(
    id: int,
    clsinput: categoryUpdateInputs,
    db: Annotated[Session, Depends(getdb)],
    current_user=Depends(require_admin)
):
    category = db.query(Categories).filter(
        Categories.id == id,
        Categories.is_deleted == False
    ).first()

    if not category:
        raise HTTPException(
            status_code=404,
            detail="Category not found"
        )

    if clsinput.name is not None:
        category.name = clsinput.name

    if clsinput.description is not None:
        category.description = clsinput.description

    if clsinput.slug is not None:
        category.slug = clsinput.slug

    try:
        db.commit()
        db.refresh(category)
        return {
            "message": "Category updated"
        }
    except Exception:
        db.rollback()
        raise


@router.delete("/categories/{id}")
def delete_category(
    id: int,
    db: Annotated[Session, Depends(getdb)],
    current_user=Depends(require_admin)
):
    category = db.query(Categories).filter(
        Categories.id == id,
        Categories.is_deleted == False
    ).first()

    if not category:
        raise HTTPException(
            status_code=404,
            detail="Category not found"
        )

    try:
        category.is_deleted = True

        db.commit()
        return {
            "message": "Category deleted"
        }
    except Exception:
        db.rollback()
        raise


@router.put("/subcategories/{id}")
def update_subcategory(
    id: int,
    clsinput: subcategoryUpdateInputs,
    db: Annotated[Session, Depends(getdb)],
    current_user=Depends(require_admin)
):
    subcategory = db.query(Sub_Categories).filter(
        Sub_Categories.id == id,
        Sub_Categories.is_deleted == False
    ).first()

    if not subcategory:
        raise HTTPException(
            status_code=404,
            detail="Subcategory not found"
        )

    if clsinput.name is not None:
        subcategory.name = clsinput.name

    if clsinput.description is not None:
        subcategory.description = clsinput.description

    if clsinput.slug is not None:
        subcategory.slug = clsinput.slug

    if clsinput.parentName is not None:
        category = db.query(Categories).filter(
            Categories.name == clsinput.parentName,
            Categories.is_deleted == False
        ).first()

        if not category:
            raise HTTPException(
                status_code=404,
                detail="Parent category not found"
            )

        subcategory.parent_id = category.id

    try:
        db.commit()
        db.refresh(subcategory)
        return {
            "message": "Subcategory updated"
        }
    except Exception:
        db.rollback()
        raise


@router.delete("/subcategories/{id}")
def delete_subcategory(
    id: int,
    db: Annotated[Session, Depends(getdb)],
    current_user=Depends(require_admin)
):
    subcategory = db.query(Sub_Categories).filter(
        Sub_Categories.id == id,
        Sub_Categories.is_deleted == False
    ).first()

    if not subcategory:
        raise HTTPException(
            status_code=404,
            detail="Subcategory not found"
        )

    try:
        subcategory.is_deleted = True

        db.commit()
        return {
            "message": "Subcategory deleted"
        }
    except Exception:
        db.rollback()
        raise

@router.get("/categories/{id}/products")
def get_category_products(
    id: int,
    db: Annotated[Session, Depends(getdb)]
):
    category = db.query(Categories).filter(
        Categories.id == id,
        Categories.is_deleted == False
    ).first()

    if not category:
        raise HTTPException(
            status_code=404,
            detail="Category not found"
        )

    products = db.query(Products).filter(
        Products.category_id == id,
        Products.is_deleted == False
    ).all()

    return {
        "data": [
            {
                "id": product.id,
                "name": product.name,
                "description": product.description,
                "summary": product.summary,
                "slug": product.slug,
                "is_featured": product.is_featured
            }
            for product in products
        ]
    }
