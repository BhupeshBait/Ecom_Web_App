from typing import Annotated,Optional
from fastapi import APIRouter, Depends, Request ,HTTPException , Form ,UploadFile ,File
from sqlalchemy.orm import Session 
from sqlalchemy import or_
from models.models import (Categories, Products,Sub_Categories,Product_Stock)
from utils.commonservices import (getdb, validate_image_file, process_images)
from fastapi.concurrency import run_in_threadpool
from core.security import (require_admin)

def build_image_url(relative_path: str, request: Request) -> str:
    path = relative_path.replace("\\", "/")
    if path.startswith("uploads/"):
        path = path[len("uploads/"):]
    return str(request.url_for("uploads", path=path))


def serialize_product(product: Products, request: Request) -> dict:
    hero_urls = {}
    for key, value in (product.hero_path or {}).items():
        hero_urls[key] = build_image_url(value, request) if value else None

    return {
        "id": product.id,
        "name": product.name,
        "summary": product.summary,
        "description": product.description,
        "category": product.category.name if product.category else None,
        "subcategory": product.subCategory.name if product.subCategory else None,
        "cover_image_url": build_image_url(product.cover_img_path, request) if product.cover_img_path else None,
        "hero_image_urls": hero_urls,
        "created_at": product.created_at,
        "updated_at": product.updated_at,
    }

max_image_size = 8 * 1024 * 1024



router = APIRouter(tags=["Products"])


@router.get("/products")
def get_all_products(
    request: Request,
    db: Annotated[Session, Depends(getdb)],
    skip: int = 0,
    limit: int = 20
):
    products = (
        db.query(Products)
        .filter(
            Products.is_deleted == False
        )
        .offset(skip)
        .limit(limit)
        .all()
    )

    return {
        "data": [
            serialize_product(
                product,
                request
            )
            for product in products
        ]
    }

@router.get("/products/search")
def search_products(
    db: Annotated[Session, Depends(getdb)],
    request: Request,
    q: Optional[str] = None
):
    if not q:
        return {"data": []}

    products = db.query(Products).filter(
        Products.is_deleted == False
    ).filter(
        or_(
            Products.name.ilike(f"%{q}%"),
            Products.summary.ilike(f"%{q}%"),
            Products.description.ilike(f"%{q}%")
        )
    ).all()

    return {"data": [serialize_product(product, request) for product in products]}


@router.get("/products/featured")
def featured_products(
    request: Request,
    db: Annotated[Session, Depends(getdb)]
):
    products = db.query(Products).filter(
        Products.is_featured == True,
        Products.is_deleted == False
    ).limit(8).all()

    return {"data": [serialize_product(product, request) for product in products]}


@router.get("/products/trending")
def trending_products(
    request: Request,
    db: Annotated[Session, Depends(getdb)]
):
    products = db.query(Products).filter(
        Products.is_deleted == False
    ).order_by(Products.updated_at.desc()).limit(8).all()

    return {"data": [serialize_product(product, request) for product in products]}


@router.get("/products/category/{category_name}")
def getProductsByCategory(
    category_name: str,
    request: Request,
    db: Annotated[Session, Depends(getdb)]
):
    category = db.query(Categories).filter(
        Categories.name == category_name
    ).first()

    if not category:
        raise HTTPException(
            status_code=404,
            detail="Category not found"
        )

    products = db.query(Products).filter(
        Products.category_id == category.id,
        Products.is_deleted == False
    ).all()

    return {"data": [serialize_product(product, request) for product in products]}


@router.get("/products/subcategory/{subcategory_name}")
def get_products_by_subcategory(
    subcategory_name: str,
    request: Request,
    db: Annotated[Session, Depends(getdb)]
):
    subcategory = db.query(Sub_Categories).filter(
        Sub_Categories.name == subcategory_name
    ).first()

    if not subcategory:
        raise HTTPException(status_code=404, detail="Subcategory not found")

    products = db.query(Products).filter(
        Products.sub_category_id == subcategory.id,
        Products.is_deleted == False
    ).all()

    return {"data": [serialize_product(product, request) for product in products]}


@router.post("/products")
async def create_product(
    request: Request,
    db: Annotated[Session, Depends(getdb)],
    current_user = Depends(require_admin),
    name: str = Form(...),
    description: str = Form(...),
    summary: str = Form(...),
    category: str = Form(...),
    subcategory: Optional[str] = Form(None),
    slug: Optional[str] = Form(None),
    is_featured: bool = Form(False),
    cover_image: UploadFile = File(...),
    hero_image_1: UploadFile = File(...),
    hero_image_2: UploadFile = File(...),
    hero_image_3: UploadFile = File(...),
    hero_image_4: UploadFile = File(...)
):
    
    try:
        category_obj = db.query(Categories).filter(
            Categories.name == category
        ).first()

        if category_obj is None:
            raise HTTPException(status_code=400, detail=f"Category '{category}' not found")

        subcategory_obj = None

        if subcategory:
            subcategory_obj = db.query(Sub_Categories).filter(
                Sub_Categories.name == subcategory
            ).first()

            if subcategory_obj is None:
                raise HTTPException(status_code=400, detail=f"Subcategory '{subcategory}' not found")

        validate_image_file(cover_image)
        
        hero_images = [
            hero_image_1,
            hero_image_2,
            hero_image_3,
            hero_image_4
        ]
        
        for idx, image in enumerate(hero_images, start=1):
            validate_image_file(image)

        cover_content = await cover_image.read()
        cover_result = await run_in_threadpool(
            process_images,
            cover_content
        )

        hero_path = {}
        for i, image in enumerate(hero_images, start=1):
            content = await image.read()

            result = await run_in_threadpool(
                process_images,
                content,
                "hero"
            )

            hero_path[f"hero_{i}"] = str(result["FilePath"])
        if slug:
            existing_slug = db.query(Products).filter(
                Products.slug == slug
            ).first()

            if existing_slug:
                raise HTTPException(
                    status_code=400,
                    detail="Slug already exists"
                )

        product = Products(
            name=name,
            description=description,
            summary=summary,
            category_id=category_obj.id,
            sub_category_id=subcategory_obj.id if subcategory_obj else None,
            cover_img_path=str(cover_result["FilePath"]),
            hero_path=hero_path,
            slug=slug,
            is_featured=is_featured
        )

        db.add(product)
        db.commit()
        db.refresh(product)

        return {
            "message": "Product added successfully",
            "product_id": product.id,
            "cover_image_url": build_image_url(product.cover_img_path, request) if product.cover_img_path else None,
            "hero_image_urls": {key: build_image_url(path, request) for key, path in (product.hero_path or {}).items()}
        }
    
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=400,
            detail=f"Error adding product: {str(e)}"
        )


@router.put("/products/{id}")
async def update_product(
    id: int,
    request: Request,
    db: Annotated[Session, Depends(getdb)],
    current_user = Depends(require_admin),
    name: Optional[str] = Form(None),
    description: Optional[str] = Form(None),
    summary: Optional[str] = Form(None),
    category: Optional[str] = Form(None),
    subcategory: Optional[str] = Form(None),
    slug: Optional[str] = Form(None),
    is_featured: Optional[bool] = Form(None),
    cover_image: Optional[UploadFile] = File(None),
    hero_image_1: Optional[UploadFile] = File(None),
    hero_image_2: Optional[UploadFile] = File(None),
    hero_image_3: Optional[UploadFile] = File(None),
    hero_image_4: Optional[UploadFile] = File(None)
):
    try:
        user=current_user
        product = db.query(Products).filter(
            Products.id == id,
            Products.is_deleted == False
        ).first()

        if not product:
            raise HTTPException(status_code=404, detail="Product not found")

        hero_images = [
            hero_image_1,
            hero_image_2,
            hero_image_3,
            hero_image_4
        ]

        updated_hero_path = {}

        for i, image in enumerate(hero_images, start=1):
            if image is not None:
                validate_image_file(image)

                content = await image.read()

                result = await run_in_threadpool(
                    process_images,
                    content,
                    "hero"
                )

                updated_hero_path[f"hero_{i}"] = str(
                    result["FilePath"]
                )

        if cover_image is not None:
            validate_image_file(cover_image)

            cover_content = await cover_image.read()

            result = await run_in_threadpool(
                process_images,
                cover_content
            )

            product.cover_img_path = str(
                result["FilePath"]
            )
        if slug:
            existing_slug = db.query(Products).filter(
                Products.slug == slug
            ).first()

            if existing_slug:
                raise HTTPException(
                    status_code=400,
                    detail="Slug already exists"
                )



        if name is not None:
            product.name = name

        if description is not None:
            product.description = description

        if summary is not None:
            product.summary = summary

        if slug is not None:
            product.slug = slug

        if is_featured is not None:
            product.is_featured = is_featured

        if category is not None:
            category_obj = db.query(Categories).filter(
                Categories.name == category
            ).first()

            if not category_obj:
                raise HTTPException(status_code=400, detail="Invalid category")

            product.category_id = category_obj.id

        if subcategory is not None:
            subcategory_obj = db.query(Sub_Categories).filter(
                Sub_Categories.name == subcategory
            ).first()

            if not subcategory_obj:
                raise HTTPException(
                    status_code=400,
                    detail="Invalid subcategory"
                )

            if category is not None:
                if subcategory_obj.parent_id != product.category_id:
                    raise HTTPException(
                        status_code=400,
                        detail="Subcategory does not belong to selected category"
                    )

            product.sub_category_id = subcategory_obj.id

        if category is not None:
            if subcategory_obj.parent_id != product.category_id:
                raise HTTPException(
                    status_code=400,
                    detail="Subcategory does not belong to selected category"
                )


            product.sub_category_id = subcategory_obj.id

        if product.hero_path is None:
            product.hero_path = {}

        product.hero_path.update(updated_hero_path)

        db.commit()
        db.refresh(product)

        return {
            "message": "Product updated successfully",
            "product_id": product.id,
            "cover_image_url": build_image_url(product.cover_img_path, request) if product.cover_img_path else None,
            "hero_image_urls": {key: build_image_url(path, request) for key, path in (product.hero_path or {}).items()}
        }
    
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=400,
            detail=f"Error updating product: {str(e)}"
        )


@router.delete("/products/{id}")
def delete_product(
    id: int,
    db: Annotated[Session, Depends(getdb)],
    current_user = Depends(require_admin)
):

    product = db.query(Products).filter(
        Products.id == id,
        Products.is_deleted == False
    ).first()

    if not product:
        raise HTTPException(
            status_code=404,
            detail="Product not found"
        )

    try:
        product.is_deleted = True

        db.commit()
        db.refresh(product)
        return {"message": "Product removed"}
    except Exception:
        db.rollback()
        raise


@router.get("/admin/products/{id}")
def getProductDetails(
    id: int,
    request: Request,
    db: Annotated[Session, Depends(getdb)],
    current_user = Depends(require_admin)
):

    product = db.query(Products).filter(
        Products.id == id,
        Products.is_deleted == False
    ).first()

    if not product:
        return {"message": "Product not found"}

    return {"data": serialize_product(product, request)}





@router.get("/products/category/{category_id}")
def get_products_by_category(
    category_id: int,
    db: Annotated[Session, Depends(getdb)]
):
    products = db.query(Products).filter(
        Products.category_id == category_id,
        Products.is_deleted == False
    ).all()

    return {
        "count": len(products),
        "products": products
    }


@router.get("/products/latest")
def latest_products(
    db: Annotated[Session, Depends(getdb)]
):
    products = db.query(Products).filter(
        Products.is_deleted == False
    ).order_by(
        Products.created_at.desc()
    ).limit(10).all()

    return {
        "count": len(products),
        "products": products
    }


@router.get("/products/filter")
def filter_products(
    min_price: float,
    max_price: float,
    db: Annotated[Session, Depends(getdb)]
):
    products = (
        db.query(Products)
        .join(Product_Stock)
        .filter(
            Products.is_deleted == False,
            Product_Stock.price >= min_price,
            Product_Stock.price <= max_price,
            Product_Stock.is_deleted == False
        )
        .all()
    )

    return {
        "count": len(products),
        "products": products
    }


@router.get("/products")
def get_products(
    db: Annotated[Session, Depends(getdb)],
    sort: str | None = None,
    skip: int = 0,
    limit: int = 20
):
    query = db.query(Products).filter(
        Products.is_deleted == False
    )

    if sort == "latest":
        query = query.order_by(
            Products.created_at.desc()
        )

    elif sort == "oldest":
        query = query.order_by(
            Products.created_at.asc()
        )

    elif sort == "name":
        query = query.order_by(
            Products.name.asc()
        )

    products = query.offset(skip).limit(limit).all()

    return {
        "count": len(products),
        "products": products
    }


@router.get("/products/slug/{slug}")
def get_product_by_slug(
    slug: str,
    db: Annotated[Session, Depends(getdb)]
):
    product = db.query(Products).filter(
        Products.slug == slug,
        Products.is_deleted == False
    ).first()

    if not product:
        raise HTTPException(
            status_code=404,
            detail="Product not found"
        )

    return product

@router.get("/products/{product_id}/related")
def related_products(
    product_id: int,
    db: Annotated[Session, Depends(getdb)]
):
    product = db.query(Products).filter(
        Products.id == product_id,
        Products.is_deleted == False
    ).first()

    if not product:
        raise HTTPException(
            status_code=404,
            detail="Product not found"
        )

    related = db.query(Products).filter(
        Products.sub_category_id == product.sub_category_id,
        Products.id != product.id,
        Products.is_deleted == False
    ).limit(4).all()

    return {
        "count": len(related),
        "products": related
    }


@router.get("/products/id/{id}")
def get_product_by_id(
    id: int,
    request: Request,
    db: Annotated[Session, Depends(getdb)]
):
    product = db.query(Products).filter(
        Products.id == id,
        Products.is_deleted == False
    ).first()

    if not product:
        raise HTTPException(
            status_code=404,
            detail="Product not found"
        )

    return {
        "data": serialize_product(
            product,
            request
        )
    }


@router.put("/admin/products/{id}/restore")
def restore_product(
    id: int,
    db: Annotated[Session, Depends(getdb)],
    current_user = Depends(require_admin)
):

    product = db.query(Products).filter(
        Products.id == id
    ).first()

    if not product:
        raise HTTPException(
            status_code=404,
            detail="Product not found"
        )

    try:
        product.is_deleted = False

        db.commit()
        return {
            "message": "Product restored"
        }
    except Exception:
        db.rollback()
        raise


