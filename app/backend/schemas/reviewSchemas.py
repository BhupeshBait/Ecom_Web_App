from datetime import date, datetime
from pydantic import BaseModel, Field
from pydantic.networks import EmailStr


class review_create_inputs(BaseModel):
    rating: int = Field(..., ge=1, le=5)
    comment: str | None = Field(None, max_length=500)


class review_update_inputs(BaseModel):
    rating: int | None = Field(None, ge=1, le=5)
    comment: str | None = Field(None, max_length=500)