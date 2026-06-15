from datetime import date, datetime
from pydantic import BaseModel, Field
from pydantic.networks import EmailStr

class categoryInputs(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    description: str = Field(..., max_length=500)
    slug: str | None = None

class SubcategoryInputs(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    description: str = Field(..., max_length=500)
    parentName: str = Field(..., min_length=1, max_length=100)
    slug: str | None = None


class categoryUpdateInputs(BaseModel):
    name: str | None = None
    description: str | None = None
    slug: str | None = None


class subcategoryUpdateInputs(BaseModel):
    name: str | None = None
    description: str | None = None
    slug: str | None = None
    parentName: str | None = None
