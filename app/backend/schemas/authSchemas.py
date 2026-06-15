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