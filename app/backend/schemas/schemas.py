from datetime import date, datetime

from pydantic import BaseModel, Field
from pydantic.networks import EmailStr


class registration_inputs(BaseModel):
    first_name: str = Field(..., min_length=1, max_length=50, description="First name")
    last_name: str = Field(..., min_length=1, max_length=50, description="Last name")
    user_name: str = Field(..., min_length=3, max_length=15, description="Username")
    contact: str = Field(..., min_length=10, max_length=15, description="Phone number")
    email: EmailStr
    password: str = Field(..., min_length=8, max_length=100, description="Password minimum 8 characters")
    DOB: date


class login_inputs(BaseModel):
    user_name: str = Field(..., min_length=3)
    password: str = Field(..., min_length=8)
    email: EmailStr | None = None


class user_update_inputs(BaseModel):
    user_name: str | None = Field(None, min_length=3, max_length=15)
    first_name: str | None = Field(None, min_length=1, max_length=50)
    last_name: str | None = Field(None, min_length=1, max_length=50)
    contact: str | None = Field(None, min_length=10, max_length=15)
    DOB: date | None = None


class address_inputs(BaseModel):
    Street: str = Field(..., max_length=100)
    City: str = Field(..., max_length=50)
    Country: str = Field(..., max_length=50)
    State: str = Field(..., max_length=50)
    Postal_code: str = Field(..., max_length=10)
    address_line_1: str = Field(..., max_length=100)
    address_line_2: str = Field(..., max_length=100)
    landmark: str = Field(..., max_length=100)
    district: str = Field(..., max_length=50)


class address_update(BaseModel):
    Street: str | None = Field(None, max_length=100)
    City: str | None = Field(None, max_length=50)
    Country: str | None = Field(None, max_length=50)
    State: str | None = Field(None, max_length=50)
    Postal_code: str | None = Field(None, max_length=10)
    address_line_1: str | None = Field(None, max_length=100)
    address_line_2: str | None = Field(None, max_length=100)
    landmark: str | None = Field(None, max_length=100)
    district: str | None = Field(None, max_length=50)


class categoryInputs(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    description: str = Field(..., max_length=500)


class SubcategoryInputs(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    description: str = Field(..., max_length=500)
    parentName: str = Field(..., min_length=1, max_length=100)


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


class order_create_inputs(BaseModel):
    address_id: int
    payment_method: str


class order_status_update_inputs(BaseModel):
    status: str
    tracking_number: str | None = None


class order_cancel_inputs(BaseModel):
    reason: str | None = None
