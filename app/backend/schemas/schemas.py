from datetime import date, datetime

from pydantic import BaseModel
from pydantic.networks import EmailStr


class registration_inputs(BaseModel):
    first_name: str
    last_name: str
    user_name: str
    contact: str
    email: EmailStr
    password: str
    DOB: date


class login_inputs(BaseModel):
    user_name: str
    password: str
    email: EmailStr | None = None


class user_update_inputs(BaseModel):
    user_name: str | None = None
    first_name: str | None = None
    last_name: str | None = None
    contact: str | None = None
    DOB: date | None = None


class address_inputs(BaseModel):
    Street: str
    City: str
    Country: str
    State: str
    Postal_code: str
    address_line_1: str
    address_line_2: str
    landmark: str
    district: str


class address_update(BaseModel):
    Street: str | None = None
    City: str | None = None
    Country: str | None = None
    State: str | None = None
    Postal_code: str | None = None
    address_line_1: str | None = None
    address_line_2: str | None = None
    landmark: str | None = None
    district: str | None = None


class categoryInputs(BaseModel):
    name: str
    description: str


class SubcategoryInputs(BaseModel):
    name: str
    description: str
    parentName: str


class addToCartInputs(BaseModel):
    quantity: int


class stock_inputs(BaseModel):
    product_id: int
    sku_id: str
    price: float
    quantity: int


class stock_update_inputs(BaseModel):
    sku_id: str | None = None
    price: float | None = None
    quantity: int | None = None
