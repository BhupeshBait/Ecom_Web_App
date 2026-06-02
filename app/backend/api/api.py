from typing import Annotated, Optional

from fastapi import APIRouter, Depends, File, Form, HTTPException, Request, UploadFile
from fastapi.concurrency import run_in_threadpool
from sqlalchemy import and_
from sqlalchemy.orm import Session
import uuid

from database.database import engine
from models import models
from models.models import (Addresses, Cart, Cart_Item, Categories,
                           Product_Stock, Products, Sub_Categories, Users, Orders, Order_Items, Payments)
from schemas.schemas import (SubcategoryInputs, address_inputs, address_update,
                             addToCartInputs, categoryInputs, login_inputs,
                             registration_inputs, stock_inputs, stock_update_inputs,
                             user_update_inputs, order_create_inputs, order_status_update_inputs, order_cancel_inputs)
from utils.commonservices import (complete_registration, get_current_user,
                                  get_token_from_header, getdb, hash_passwd,
                                  process_images, validate_contact,
                                  validate_image_file, validate_username,
                                  verify_password)
from utils.token import create_token

models.base.metadata.create_all(bind=engine)


router = APIRouter()


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
countryList = {
    "India": [
        "Maharashtra",
        "Karnataka",
        "Tamil Nadu",
        "Uttar Pradesh",
        "Gujarat",
        "Rajasthan",
        "West Bengal",
        "Punjab",
        "Bihar",
        "Kerala"
    ],
    "United States": [
        "California",
        "Texas",
        "Florida",
        "New York",
        "Illinois",
        "Pennsylvania",
        "Ohio",
        "Georgia",
        "North Carolina",
        "Michigan"
    ]
}

# |---------------------------User API's------------------------------|


@router.post('/user/register')
async def sign_in(db: Annotated[Session, Depends(
        getdb)], clsinput: registration_inputs):
    inputs = Users(
        first_name=clsinput.first_name,
        last_name=clsinput.last_name,
        user_name=clsinput.user_name,
        email=clsinput.email,
        contact=clsinput.contact,
        hash_password=hash_passwd(clsinput.password),
        DOB=clsinput.DOB
    )
    result = complete_registration(
        email=clsinput.email,
        username=clsinput.user_name,
        contact=str(
            clsinput.contact),
        first_name=clsinput.first_name,
        last_name=clsinput.last_name,
        db=db)
    if result == "Done":
        db.add(inputs)
        db.commit()
        db.refresh(inputs)
        return {"message": f"{clsinput.user_name} registered!"}
    return result


@router.post('/user/login')
def log_in(db: Annotated[Session, Depends(getdb)], clsinput: login_inputs):
    username = clsinput.user_name
    password = clsinput.password
    email = clsinput.email
    result = verify_password(
        password=password,
        username=username,
        email=email,
        db=db)

    if result is None:
        user = db.query(Users).filter(Users.user_name == username).first()
        if user is None:
            raise HTTPException(status_code=401, detail="Invalid login credentials")
        token = create_token(user.user_name, user.email)
        return {"message": "Logged In!",
                "token": token}
    return result


@router.get('/user/profile')
def getUser(db: Annotated[Session, Depends(getdb)], token: str = Depends(get_token_from_header)):
    user = get_current_user(token=token, db=db)
    if not user:
        raise HTTPException(status_code=404, detail="User not Found")
    return {"Username": user.user_name,
            "Contact": user.contact,
            "User_id": user.id,
            "First_name": user.first_name,
            "Last_name": user.last_name}


@router.put('/user/profile/update')
def updateUser(
    db: Annotated[Session, Depends(getdb)],
    clsinput: user_update_inputs,
    token: str = Depends(get_token_from_header)
):
    user = get_current_user(token=token, db=db)

    if not user:
        raise HTTPException(status_code=404, detail="User not Found")

    if clsinput.user_name is not None:
        existing_user = db.query(Users).filter(
            Users.user_name == clsinput.user_name,
            Users.id != user.id
        ).first()

        if existing_user:
            return {"message": "Username already taken"}

        if not validate_username(clsinput.user_name):
            return {"message": "Invalid username"}

        user.user_name = clsinput.user_name

    if clsinput.first_name is not None:
        user.first_name = clsinput.first_name

    if clsinput.last_name is not None:
        user.last_name = clsinput.last_name

    if clsinput.contact is not None:
        if not validate_contact(clsinput.contact):
            return {"message": "Invalid contact"}

        user.contact = clsinput.contact

    if clsinput.DOB is not None:
        user.DOB = clsinput.DOB

    db.commit()
    db.refresh(user)

    return {"message": "User updated successfully"}


# |--------------------------------Addresses API's------------------------------------|


@router.post('/add/address')
def add_address(db: Annotated[Session, Depends(
        getdb)], clsinput: address_inputs, token: str = Depends(get_token_from_header)):
    user = get_current_user(token=token, db=db)
    if not user:
        raise HTTPException(status_code=404, detail="User not Found")
    user_inputs = Addresses(
        user_id=user.id,
        street=clsinput.Street,
        city=clsinput.City,
        state=clsinput.State,
        country=clsinput.Country,
        postal_code=clsinput.Postal_code,
        address_line_1=clsinput.address_line_1,
        address_line_2=clsinput.address_line_2,
        district=clsinput.district,
        landmark=clsinput.landmark
    )
    if not clsinput.Country in countryList.keys():
        return {"message": "Enter a valid Country name"}

    if not clsinput.State in countryList[clsinput.Country]:
        return {"message": "Enetr a valid State name"}

    db.add(user_inputs)
    db.commit()
    db.refresh(user_inputs)
    return {"message": "Address added!"}


@router.get('/get/addresses')
def get_address(db: Annotated[Session, Depends(getdb)], token: str = Depends(get_token_from_header)):
    user = get_current_user(token=token, db=db)
    if not user:
        raise HTTPException(status_code=404, detail="User not Found")
    result = db.query(Addresses).filter(
        and_(
            Addresses.user_id == user.id,
            Addresses.is_deleted == False)).all()
    return {"Addresses": result}


@router.put('/update/address/{id}')
def updateAddress(
    id: int,
    clsinput: address_update,
    db: Annotated[Session, Depends(getdb)],
    token: str = Depends(get_token_from_header)
):
    user = get_current_user(token=token, db=db)
    if not user:
        raise HTTPException(status_code=404, detail="USer not Found")
    address = db.query(Addresses).filter(
        Addresses.id == id,
        Addresses.user_id == user.id,
        Addresses.is_deleted == False
    ).first()

    if not address:
        return {"message": "Address not found"}

    if clsinput.Country is not None:
        if clsinput.Country not in countryList:
            return {"message": "Invalid country"}

        address.country = clsinput.Country

    if clsinput.State is not None:
        country = clsinput.Country or address.country

        if country not in countryList:
            return {"message": "Invalid country"}

        if clsinput.State not in countryList[country]:
            return {"message": "Invalid state"}

        address.state = clsinput.State

    if clsinput.City is not None:
        address.city = clsinput.City

    if clsinput.Street is not None:
        address.street = clsinput.Street

    if clsinput.Postal_code is not None:
        address.postal_code = clsinput.Postal_code

    if clsinput.address_line_1 is not None:
        address.address_line_1 = clsinput.address_line_1

    if clsinput.address_line_2 is not None:
        address.address_line_2 = clsinput.address_line_2

    if clsinput.landmark is not None:
        address.landmark = clsinput.landmark

    if clsinput.district is not None:
        address.district = clsinput.district

    db.commit()
    db.refresh(address)

    return {"message": "Address updated"}


@router.put('/remove/address/{id}')
def deleteAddress(id: int, db: Annotated[Session, Depends(getdb)], token: str = Depends(get_token_from_header)):
    user = get_current_user(token=token, db=db)
    if not user:
        raise HTTPException(status_code=404, detail="USer not Found")
    address = db.query(Addresses).filter(
        and_(Addresses.id == id, Addresses.user_id == user.id)).first()
    if address:
        address.is_deleted = True
    db.commit()
    return {"message": "Address removed"}


# |-----------------------------Categories API's--------------------------------|


@router.post("/add/categories")
def addCategories(db: Annotated[Session, Depends(
        getdb)], clsinput: categoryInputs):
    categoryInput = Categories(
        name=clsinput.name,
        description=clsinput.description
    )
    alreadyExist = bool(db.query(Categories).filter(
        Categories.name == clsinput.name).first())
    if alreadyExist is False:
        db.add(categoryInput)
        db.commit()
        db.refresh(categoryInput)
        return {"message": "Category Added"}
    else:
        return {"message": "category already exsist"}


@router.post('/add/subcategories')
def addSubcategory(db: Annotated[Session, Depends(
        getdb)], clsinput: SubcategoryInputs):
    category_id = db.query(Categories).filter(
        Categories.name == clsinput.parentName).first()
    if category_id is None:
        return {"message": 'Enter a valid Category Name'}

    subCategoryinput = Sub_Categories(
        name=clsinput.name,
        parent_id=category_id.id,
        description=clsinput.description
    )

    alreadyExistsub = bool(
        db.query(Sub_Categories).filter(
            Sub_Categories.name == clsinput.name).first())
    if alreadyExistsub:
        return {"message": "Sub category already exsist"}
    else:
        db.add(subCategoryinput)
        db.commit()
        db.refresh(subCategoryinput)
        return {"message": "Subcategory and Category added"}


#  |-------------------------------Product API's------------------------------------


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
        return {"message": "Category not found"}

    products = db.query(Products).filter(
        Products.category_id == category.id,
        Products.is_deleted == False
    ).all()

    return {"data": [serialize_product(product, request) for product in products]}


# |----------------------------------Admin Product API's-------------------------------|


@router.post("/stock/add")
def addStock(db: Annotated[Session, Depends(getdb)], clsinput: stock_inputs, token: str = Depends(get_token_from_header)):
    user = get_current_user(token=token, db=db)
    if not user:
        raise HTTPException(status_code=404, detail="User not Found")
    
    if user.role.value != "admin":
        raise HTTPException(status_code=403, detail="Only admins can add stock")
    
    product = db.query(Products).filter(
        and_(
            Products.id == clsinput.product_id,
            Products.is_deleted == False
        )
    ).first()
    
    if not product:
        return {"message": "Product not found"}
    
    existing_sku = db.query(Product_Stock).filter(
        Product_Stock.sku_id == clsinput.sku_id
    ).first()
    
    if existing_sku:
        return {"message": "SKU already exists"}
    
    stock = Product_Stock(
        product_id=clsinput.product_id,
        sku_id=clsinput.sku_id,
        price=clsinput.price,
        quantity=clsinput.quantity
    )
    
    db.add(stock)
    db.commit()
    db.refresh(stock)
    
    return {"message": "Stock added successfully", "stock_id": stock.id}


@router.put("/stock/update/{product_stock_id}")
def updateStock(
    product_stock_id: int,
    db: Annotated[Session, Depends(getdb)],
    clsinput: stock_update_inputs,
    token: str = Depends(get_token_from_header)
):
    user = get_current_user(token=token, db=db)
    if not user:
        raise HTTPException(status_code=404, detail="User not Found")
    
    if user.role.value != "admin":
        raise HTTPException(status_code=403, detail="Only admins can update stock")
    
    stock = db.query(Product_Stock).filter(
        and_(
            Product_Stock.id == product_stock_id,
            Product_Stock.is_deleted == False
        )
    ).first()
    
    if not stock:
        return {"message": "Stock not found"}
    
    if clsinput.sku_id is not None:
        existing_sku = db.query(Product_Stock).filter(
            and_(
                Product_Stock.sku_id == clsinput.sku_id,
                Product_Stock.id != product_stock_id
            )
        ).first()
        
        if existing_sku:
            return {"message": "SKU already exists"}
        
        stock.sku_id = clsinput.sku_id
    
    if clsinput.price is not None:
        stock.price = clsinput.price
    
    if clsinput.quantity is not None:
        stock.quantity = clsinput.quantity
    
    db.commit()
    db.refresh(stock)
    
    return {"message": "Stock updated successfully"}


@router.get("/stock/get/{product_id}")
def getStock(product_id: int, db: Annotated[Session, Depends(getdb)], token: str = Depends(get_token_from_header)):
    user = get_current_user(token=token, db=db)
    if not user:
        raise HTTPException(status_code=404, detail="User not Found")
    
    if user.role.value != "admin":
        raise HTTPException(status_code=403, detail="Only admins are allowed to get stock details")
    product = db.query(Products).filter(
        and_(
            Products.id == product_id,
            Products.is_deleted == False
        )
    ).first()
    
    if not product:
        return {"message": "Product not found"}
    
    stocks = db.query(Product_Stock).filter(
        and_(
            Product_Stock.product_id == product_id,
            Product_Stock.is_deleted == False
        )
    ).all()
    
    return {"data": stocks}


@router.put("/stock/remove/{product_stock_id}")
def deleteStock(product_stock_id: int, db: Annotated[Session, Depends(getdb)], token: str = Depends(get_token_from_header)):
    user = get_current_user(token=token, db=db)
    if not user:
        raise HTTPException(status_code=404, detail="User not Found")
    
    if user.role.value != "admin":
        raise HTTPException(status_code=403, detail="Only admins can delete stock")
    
    stock = db.query(Product_Stock).filter(
        and_(
            Product_Stock.id == product_stock_id,
            Product_Stock.is_deleted == False
        )
    ).first()
    
    if not stock:
        return {"message": "Stock not found"}
    
    stock.is_deleted = True
    db.commit()
    
    return {"message": "Stock deleted successfully"}


@router.post("/add/products")
async def addProducts(
    request: Request,
    db: Annotated[Session, Depends(getdb)],
    token: str = Depends(get_token_from_header),
    name: str = Form(...),
    description: str = Form(...),
    summary: str = Form(...),
    category: str = Form(...),
    subcategory: Optional[str] = Form(None),
    cover_image: UploadFile = File(...),
    hero_image_1: UploadFile = File(...),
    hero_image_2: UploadFile = File(...),
    hero_image_3: UploadFile = File(...),
    hero_image_4: UploadFile = File(...)
):
    user = get_current_user(token=token, db=db)
    if user.role.value != "admin":
        raise HTTPException(status_code=403, detail="Only admins can add products")
    
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

        product = Products(
            name=name,
            description=description,
            summary=summary,
            category_id=category_obj.id,
            sub_category_id=subcategory_obj.id if subcategory_obj else None,
            cover_img_path=str(cover_result["FilePath"]),
            hero_path=hero_path
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


@router.put("/update/products/{id}")
async def updateProducts(
    id: int,
    request: Request,
    db: Annotated[Session, Depends(getdb)],
    token: str = Depends(get_token_from_header),
    name: Optional[str] = Form(None),
    description: Optional[str] = Form(None),
    summary: Optional[str] = Form(None),
    category: Optional[str] = Form(None),
    subcategory: Optional[str] = Form(None),
    cover_image: Optional[UploadFile] = File(None),
    hero_image_1: Optional[UploadFile] = File(None),
    hero_image_2: Optional[UploadFile] = File(None),
    hero_image_3: Optional[UploadFile] = File(None),
    hero_image_4: Optional[UploadFile] = File(None)
):
    user = get_current_user(token=token, db=db)
    if user.role.value != "admin":
        raise HTTPException(status_code=403, detail="Only admins can update products")
    try:
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

        if name is not None:
            product.name = name

        if description is not None:
            product.description = description

        if summary is not None:
            product.summary = summary

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
                raise HTTPException(status_code=400, detail="Invalid subcategory")

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


@router.put("/removeProduct/{id}")
def removeProduct(
    id: int,
    db: Annotated[Session, Depends(getdb)],
    token: str = Depends(get_token_from_header)
):
    user = get_current_user(token=token, db=db)
    if user.role.value != "admin":
        raise HTTPException(status_code=403, detail="Only admins can remove products")

    product = db.query(Products).filter(
        Products.id == id,
        Products.is_deleted == False
    ).first()

    if not product:
        return {"message": "Product not found"}

    product.is_deleted = True

    db.commit()
    db.refresh(product)

    return {"message": "Product removed"}


@router.get("/admin/get/products")
def getProducts(
    request: Request,
    db: Annotated[Session, Depends(getdb)],
    token: str = Depends(get_token_from_header),
    skip: int = 0,
    limit: int = 10
):
    user = get_current_user(token=token, db=db)
    if user.role.value != "admin":
        raise HTTPException(status_code=403, detail="Only admins can view products")

    products = db.query(Products).filter(
        Products.is_deleted == False
    ).offset(skip).limit(limit).all()

    return {"data": [serialize_product(product, request) for product in products]}


@router.get("/admin/get/productDetails/{id}")
def getProductDetails(
    id: int,
    request: Request,
    db: Annotated[Session, Depends(getdb)],
    token: str = Depends(get_token_from_header)
):
    user = get_current_user(token=token, db=db)
    if user.role.value != "admin":
        raise HTTPException(status_code=403, detail="Only admins can view product details")

    product = db.query(Products).filter(
        Products.id == id,
        Products.is_deleted == False
    ).first()

    if not product:
        return {"message": "Product not found"}

    return {"data": serialize_product(product, request)}


# |-------------------------------------------Cart API's---------------------------------|


@router.post("/cart/add/{product_id}")
def addToCart(product_id: int, quantity: int,
              db: Annotated[Session, Depends(getdb)], clsinput: addToCartInputs,
              token: str = Depends(get_token_from_header)):
    user = get_current_user(token=token, db=db)
    if not user:
        raise HTTPException(status_code=404, detail="User not Found")
    product = db.query(Products).filter(
        and_(
            Products.id == product_id,
            Products.is_deleted == False)).first()
    product_stock = db.query(Product_Stock).filter(
        and_(
            Product_Stock.product_id == product_id,
            Product_Stock.is_deleted == False)).first()
    if not product:
        return {"message": "Product not found"}
    
    if not product_stock:
        return {"message": "Product stock not found"}

    cart = db.query(Cart).filter(Cart.user_id == user.id).first()
    if not cart:
        cart = Cart(user_id=user.id, total=0)
        db.add(cart)
        db.commit()
        db.refresh(cart)

    cart_item = Cart_Item(
        cart_id=cart.id,
        product_id=product.id,
        quantity=clsinput.quantity,
        product_stock_id=product_stock.id
    )

    if not cart_item:
        raise HTTPException(status_code=404, detail="Item not found")

    cart.total += product_stock.price * clsinput.quantity
    db.add(cart_item)
    db.commit()
    db.refresh(cart_item)
    return {"message": "Product added to cart!"}


@router.get('/cart/get')
def getCart(db: Annotated[Session, Depends(getdb)], token: str = Depends(get_token_from_header)):
    user = get_current_user(token=token, db=db)
    if not user:
        raise HTTPException(status_code=404, detail="User not Found")
    cart = db.query(Cart).filter(Cart.user_id == user.id).first()
    cart_Items = db.query(Cart_Item).filter(
        and_(
            Cart_Item.is_deleted == False,
            Cart_Item.cart_id == cart.id)).all()
    return {"items": cart_Items,
            "total":cart.total}


@router.put('/cart/update/{cart_item_id}')
def cartUpdate(cart_item_id: int,
               db: Annotated[Session, Depends(getdb)], quantity: int = Form(...),
               token: str = Depends(get_token_from_header)):
    user = get_current_user(token=token, db=db)
    if not user:
        raise HTTPException(status_code=404, detail="User not Found")
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
    db.commit()
    return {"message": "Cart updated",
            "cart_total": cart.total}

@router.put("/CartItem/remove/{cart_item_id}")
def removeItem(cart_item_id: int,
               db: Annotated[Session, Depends(getdb)],
               token: str = Depends(get_token_from_header)):
    user = get_current_user(token=token, db=db)
    if not user:
        raise HTTPException(status_code=404, detail="User not Found")
    cart = db.query(Cart).filter(Cart.user_id == user.id).first() 
    cart_item = db.query(Cart_Item).join(Cart).filter(
        Cart_Item.id == cart_item_id,
        Cart.user_id == user.id).first()
    if not cart_item:
        raise HTTPException(status_code=404, detail="Item not found")
    cart_item.is_deleted=True
    
    cart.total=cart.total-(cart_item.quantity*cart_item.productStock.price)
    db.commit()
    return {'Msg':"Item removed"}

@router.put("/cart/clear")
def clearCart(db: Annotated[Session, Depends(getdb)], token: str = Depends(get_token_from_header)):
    user = get_current_user(token=token, db=db)
    if not user:
        raise HTTPException(status_code=404, detail="User not Found")
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
    db.commit()
    return {"message":"Cart cleared!"}

# |--------------------------------Order API's------------------------------------|

@router.post("/order/create")
def createOrder(db: Annotated[Session, Depends(getdb)], clsinput: order_create_inputs,
                token: str = Depends(get_token_from_header)):
    user = get_current_user(token=token, db=db)
    if not user:
        raise HTTPException(status_code=404, detail="User not Found")
    
    address = db.query(Addresses).filter(
        and_(
            Addresses.id == clsinput.address_id,
            Addresses.user_id == user.id,
            Addresses.is_deleted == False
        )
    ).first()
    
    if not address:
        return {"message": "Address not found"}
    
    cart = db.query(Cart).filter(Cart.user_id == user.id).first()
    if not cart:
        return {"message": "Cart is empty"}
    
    cart_items = db.query(Cart_Item).filter(
        and_(
            Cart_Item.cart_id == cart.id,
            Cart_Item.is_deleted == False
        )
    ).all()
    
    if not cart_items:
        return {"message": "No items in cart"}
    
    for item in cart_items:
        stock = db.query(Product_Stock).filter(
            Product_Stock.id == item.product_stock_id
        ).first()
        if not stock or stock.quantity < item.quantity:
            return {"message": f"Insufficient stock for product {item.product.name}"}
    
    order_number = f"ORD-{uuid.uuid4().hex[:10].upper()}"
    total_amount = cart.total
    
    order = Orders(
        user_id=user.id,
        order_number=order_number,
        status="PENDING",
        total_amount=total_amount,
        final_amount=total_amount,
        shipping_address_id=address.id
    )
    
    db.add(order)
    db.flush()
    
    for cart_item in cart_items:
        order_item = Order_Items(
            user_id=user.id,
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


@router.get("/order/list")
def getUserOrders(db: Annotated[Session, Depends(getdb)], skip: int = 0, limit: int = 10,
                  token: str = Depends(get_token_from_header)):
    user = get_current_user(token=token, db=db)
    if not user:
        raise HTTPException(status_code=404, detail="User not Found")
    
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
                    token: str = Depends(get_token_from_header)):
    user = get_current_user(token=token, db=db)
    if not user:
        raise HTTPException(status_code=404, detail="User not Found")
    
    order = db.query(Orders).filter(
        and_(
            Orders.id == order_id,
            Orders.user_id == user.id,
            Orders.is_deleted == False
        )
    ).first()
    
    if not order:
        return {"message": "Order not found"}
    
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
                      token: str = Depends(get_token_from_header)):
    user = get_current_user(token=token, db=db)
    if not user:
        raise HTTPException(status_code=404, detail="User not Found")
    
    if user.role.value != "admin":
        raise HTTPException(status_code=403, detail="Only admins can update order status")
    
    order = db.query(Orders).filter(
        and_(
            Orders.id == order_id,
            Orders.is_deleted == False
        )
    ).first()
    
    if not order:
        return {"message": "Order not found"}
    
    valid_statuses = ["PENDING", "PROCESSING", "SHIPPED", "DELIVERED", "CANCELED"]
    if clsinput.status not in valid_statuses:
        return {"message": f"Invalid status. Valid statuses are: {', '.join(valid_statuses)}"}
    
    order.status = clsinput.status
    
    if clsinput.tracking_number:
        payment = db.query(Payments).filter(Payments.order_id == order.id).first()
        if not payment:
            payment = Payments(
                order_id=order.id,
                payment_method=clsinput.tracking_number,
                amount=order.total_amount,
                status="INITIATED"
            )
            db.add(payment)
    
    db.commit()
    db.refresh(order)
    
    return {
        "order_id": order.id,
        "status": order.status,
        "status_updated_at": order.updated_at,
        "message": "Order status updated successfully"
    }


@router.put("/order/{order_id}/cancel")
def cancelOrder(order_id: int, db: Annotated[Session, Depends(getdb)],
                 clsinput: order_cancel_inputs,
                 token: str = Depends(get_token_from_header)):
    user = get_current_user(token=token, db=db)
    if not user:
        raise HTTPException(status_code=404, detail="User not Found")
    
    order = db.query(Orders).filter(
        and_(
            Orders.id == order_id,
            Orders.user_id == user.id,
            Orders.is_deleted == False
        )
    ).first()
    
    if not order:
        return {"message": "Order not found"}
    
    if order.status not in ["PENDING", "PROCESSING"]:
        return {"message": f"Cannot cancel order with status {order.status}"}
    
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
    
    order.status = "CANCELED"
    order.reason=clsinput.reason
    
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

@router.get("/order/get/{status}")
def get_order_with_status(status: str, db: Annotated[Session, Depends(getdb)],
                          token: str = Depends(get_token_from_header)):
    user = get_current_user(token=token, db=db)
    if not user:
        raise HTTPException(status_code=404, detail="User not Found")
    
    order = db.query(Orders).filter(
        and_(
            Orders.status==status,
            Orders.user_id == user.id,
            Orders.is_deleted == False
        )
    ).all()

    if not order:
        return {"message": "Order not found"}
    
    return{"Orders":order}
    

