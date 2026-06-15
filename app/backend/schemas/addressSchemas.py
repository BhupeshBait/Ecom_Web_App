from datetime import date, datetime
from pydantic import BaseModel, Field
from pydantic.networks import EmailStr


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