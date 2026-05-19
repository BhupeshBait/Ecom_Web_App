from typing import Annotated, Optional

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from fastapi.concurrency import run_in_threadpool
from sqlalchemy import and_
from sqlalchemy.orm import Session

from database.database import engine
from models import models
from models.models import (Addresses, Cart, Cart_Item, Categories,
                           Product_Stock, Products, Sub_Categories, Users)
from schemas.schemas import (SubcategoryInputs, address_inputs, address_update,
                             addToCartInputs, categoryInputs, login_inputs,
                             registration_inputs, user_update_inputs)
from utils.commonservices import (complete_registration, get_current_user,
                                  getdb, hash_passwd, process_images,
                                  validate_contact, validate_image_file,
                                  validate_username, verify_password)
from utils.token import create_token

models.base.metadata.create_all(bind=engine)


router = APIRouter()

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


@router.post('/signin')
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
        return {"Msg": f"{clsinput.user_name} registered!"}
    return result


@router.post('/login')
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
        token = create_token(username, email)
        return {"Msg": "Logged In!",
                "token": token}
    return result


@router.get('/profile/{token}')
def getUser(token: str, db: Annotated[Session, Depends(getdb)]):
    user = get_current_user(token=token, db=db)
    if not user:
        raise HTTPException(status_code=404, detail="USer not Found")
    return {"Username": user.user_name,
            "Contact": user.contact,
            "User_id": user.id,
            "First_name": user.first_name,
            "Last_name": user.last_name}


@router.put('/update/{token}')
def updateUser(
    token: str,
    db: Annotated[Session, Depends(getdb)],
    clsinput: user_update_inputs
):
    user = get_current_user(token=token, db=db)

    if not user:
        raise HTTPException(status_code=404, detail="USer not Found")

    if clsinput.user_name is not None:
        existing_user = db.query(Users).filter(
            Users.user_name == clsinput.user_name,
            Users.id != user.id
        ).first()

        if existing_user:
            return {"msg": "Username already taken"}

        if not validate_username(clsinput.user_name):
            return {"msg": "Invalid username"}

        user.user_name = clsinput.user_name

    if clsinput.first_name is not None:
        user.first_name = clsinput.first_name

    if clsinput.last_name is not None:
        user.last_name = clsinput.last_name

    if clsinput.contact is not None:
        if not validate_contact(clsinput.contact):
            return {"msg": "Invalid contact"}

        user.contact = clsinput.contact

    if clsinput.DOB is not None:
        user.DOB = clsinput.DOB

    db.commit()
    db.refresh(user)

    return {"msg": "User updated successfully"}


# |--------------------------------Addresses API's------------------------------------|


@router.post('/add_Address/{token}')
def add_address(token: str, db: Annotated[Session, Depends(
        getdb)], clsinput: address_inputs):
    user = get_current_user(token=token, db=db)
    if not user:
        raise HTTPException(status_code=404, detail="USer not Found")
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
        return {"Msg": "Enter a valid Country name"}

    if not clsinput.State in countryList[clsinput.Country]:
        return {"Msg": "Enetr a valid State name"}

    db.add(user_inputs)
    db.commit()
    db.refresh(user_inputs)
    return {"Msg": "Address added!"}


@router.get('/Addresses/{token}')
def get_address(token: str, db: Annotated[Session, Depends(getdb)]):
    user = get_current_user(token=token, db=db)
    if not user:
        raise HTTPException(status_code=404, detail="USer not Found")
    result = db.query(Addresses).filter(
        and_(
            Addresses.user_id == user.id,
            Addresses.is_deleted == False)).all()
    return {"Addresses": result}


@router.put('/UpdateAddress/{token}/{id}')
def updateAddress(
    token: str,
    id: int,
    db: Annotated[Session, Depends(getdb)],
    clsinput: address_update
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
        return {"msg": "Address not found"}

    if clsinput.Country is not None:
        if clsinput.Country not in countryList:
            return {"msg": "Invalid country"}

        address.country = clsinput.Country

    if clsinput.State is not None:
        country = clsinput.Country or address.country

        if country not in countryList:
            return {"msg": "Invalid country"}

        if clsinput.State not in countryList[country]:
            return {"msg": "Invalid state"}

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

    return {"msg": "Address updated"}


@router.put('/deleteAddress/{token}/{id}')
def deleteAddress(token: str, id: int, db: Annotated[Session, Depends(getdb)]):
    user = get_current_user(token=token, db=db)
    if not user:
        raise HTTPException(status_code=404, detail="USer not Found")
    address = db.query(Addresses).filter(
        and_(Addresses.id == id, Addresses.user_id == user.id)).first()
    if address:
        address.is_deleted = True
    db.commit()
    return {"Msg": "Address removed"}


# |-----------------------------Categories API's--------------------------------|


@router.post("/addCategories/")
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
        return {"msg": "Category Added"}
    else:
        return {"msg": "category already exsist"}


@router.post('/addSubcategories/')
def addSubcategory(db: Annotated[Session, Depends(
        getdb)], clsinput: SubcategoryInputs):
    category_id = db.query(Categories).filter(
        Categories.name == clsinput.parentName).first()
    if category_id is None:
        return {"msg": 'Enter a valid Category Name'}

    subCategoryinput = Sub_Categories(
        name=clsinput.name,
        parent_id=category_id.id,
        description=clsinput.description
    )

    alreadyExistsub = bool(
        db.query(Sub_Categories).filter(
            Sub_Categories.name == clsinput.name).first())
    if alreadyExistsub:
        return {"Msg": "Sub category already exsist"}
    else:
        db.add(subCategoryinput)
        db.commit()
        db.refresh(subCategoryinput)
        return {"Msg": "Subcategory and Category added"}

# |-------------------------------Product API's------------------------------------|


@router.post("/addProducts/")
async def addProducts(
    db: Annotated[Session, Depends(getdb)],
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
    hero_path = {}

    hero_images = [
        hero_image_1,
        hero_image_2,
        hero_image_3,
        hero_image_4
    ]

    validate_image_file(cover_image)

    for image in hero_images:
        validate_image_file(image)

    category_obj = db.query(Categories).filter(
        Categories.name == category
    ).first()

    if category_obj is None:
        return {"msg": "Enter valid category"}

    subcategory_obj = None

    if subcategory:
        subcategory_obj = db.query(Sub_Categories).filter(
            Sub_Categories.name == subcategory
        ).first()

        if subcategory_obj is None:
            return {"msg": "Enter valid subcategory"}

    for i, image in enumerate(hero_images, start=1):
        content = await image.read()

        result = await run_in_threadpool(
            process_images,
            content,
            "hero"
        )

        hero_path[f"hero_{i}"] = str(result["FilePath"])

    cover_content = await cover_image.read()

    cover_result = await run_in_threadpool(
        process_images,
        cover_content
    )

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
        "msg": "Product added successfully",
        "product_id": product.id
    }


@router.put("/updateProducts/{id}")
async def updateProducts(
    id: int,
    db: Annotated[Session, Depends(getdb)],
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
    product = db.query(Products).filter(
        Products.id == id,
        Products.is_deleted == False
    ).first()

    if not product:
        return {"msg": "Product not found"}

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
            return {"msg": "Invalid category"}

        product.category_id = category_obj.id

    if subcategory is not None:
        subcategory_obj = db.query(Sub_Categories).filter(
            Sub_Categories.name == subcategory
        ).first()

        if not subcategory_obj:
            return {"msg": "Invalid subcategory"}

        product.sub_category_id = subcategory_obj.id

    if product.hero_path is None:
        product.hero_path = {}

    product.hero_path.update(updated_hero_path)

    db.commit()
    db.refresh(product)

    return {"msg": "Product updated successfully"}


@router.put("/removeProduct/{id}")
def removeProduct(
    id: int,
    db: Annotated[Session, Depends(getdb)]
):
    product = db.query(Products).filter(
        Products.id == id,
        Products.is_deleted == False
    ).first()

    if not product:
        return {"msg": "Product not found"}

    product.is_deleted = True

    db.commit()
    db.refresh(product)

    return {"msg": "Product removed"}


@router.get("/products/category/{category_name}")
def getProductsByCategory(
    category_name: str,
    db: Annotated[Session, Depends(getdb)]
):
    category = db.query(Categories).filter(
        Categories.name == category_name
    ).first()

    if not category:
        return {"msg": "Category not found"}

    products = db.query(Products).filter(
        Products.category_id == category.id,
        Products.is_deleted == False
    ).all()

    return {"data": products}


# |----------------------------------Admin Product API's-------------------------------|


@router.get("/admin/getProducts/")
def getProducts(
    db: Annotated[Session, Depends(getdb)],
    skip: int = 0,
    limit: int = 10
):
    products = db.query(Products).filter(
        Products.is_deleted == False
    ).offset(skip).limit(limit).all()

    return {"data": products}


@router.get("/admin/getProductDetails/{id}")
def getProductDetails(
    id: int,
    db: Annotated[Session, Depends(getdb)]
):
    product = db.query(Products).filter(
        Products.id == id,
        Products.is_deleted == False
    ).first()

    if not product:
        return {"msg": "Product not found"}

    return {"data": product}


# |-------------------------------------------Cart API's---------------------------------|


@router.post("/addToCart/{token}/{product_id}")
def addToCart(token: str, product_id: int, quantity: int,
              db: Annotated[Session, Depends(getdb)], clsinput: addToCartInputs):
    user = get_current_user(token=token, db=db)
    if not user:
        raise HTTPException(status_code=404, detail="USer not Found")
    product = db.query(Products).filter(
        and_(
            Products.id == product_id,
            Products.is_deleted == False)).first()
    product_stock = db.query(Product_Stock).filter(
        and_(
            Product_Stock.product_id == product_id,
            Product_Stock.is_deleted == False)).first()
    if not product:
        return {"Msg": "Product not found"}

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

    cart.total += product_stock.price * clsinput.quantity
    db.add(cart_item)
    db.commit()
    db.refresh(cart_item)
    return {"Msg": "Product added to cart!"}


@router.get('/getCart/{token}')
def getCart(token: str, db: Annotated[Session, Depends(getdb)]):
    user = get_current_user(token=token, db=db)
    if not user:
        raise HTTPException(status_code=404, detail="USer not Found")
    cart = db.query(Cart).filter(Cart.user_id == user.id).first()
    cart_Items = db.query(Cart_Item).filter(
        and_(
            Cart_Item.is_deleted == False,
            Cart_Item.cart_id == cart.id)).all()
    return {"items": cart_Items}


@router.put('/updateCart/{cart_item_id}/{token}')
def cartUpdate(cart_item_id: int, token: str,
               db: Annotated[Session, Depends(getdb)], quantity: int = Form(...)):
    user = get_current_user(token=token, db=db)
    if not user:
        raise HTTPException(status_code=404, detail="USer not Found")
    cart_item = db.query(Cart_Item).filter(
        Cart_Item.id == cart_item_id,
        Cart.user_id == user.id).first()
    if not cart_item:
        raise HTTPException(status_code=404, detail="Item not found")
    if quantity > Cart_Item.productStock.quantity:
        raise HTTPException(status_code=409, detail="Insufficient Stock")
    cart_item.quantity = quantity
    cart = cart_item.cart
    items = db.query(Cart_Item).filter(
        and_(
            Cart_Item.cart_id == cart.id,
            Cart_Item.is_deleted == False)).all()
    cart.total = sum(
        item.quantity *
        items.productStock.price for item in items)
    db.commit()
    return {"Msg": "Cart updated",
            "Cart Total :": cart.total}
