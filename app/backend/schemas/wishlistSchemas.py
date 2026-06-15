from datetime import date, datetime
from pydantic import BaseModel, Field
from pydantic.networks import EmailStr


class wishlist_inputs(BaseModel):
    product_id: int