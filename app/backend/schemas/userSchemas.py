from datetime import date, datetime
from pydantic import BaseModel, Field
from pydantic.networks import EmailStr


class user_update_inputs(BaseModel):
    user_name: str | None = Field(None, min_length=3, max_length=15)
    first_name: str | None = Field(None, min_length=1, max_length=50)
    last_name: str | None = Field(None, min_length=1, max_length=50)
    contact: str | None = Field(None, min_length=10, max_length=15)
    DOB: date | None = None