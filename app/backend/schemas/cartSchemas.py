from datetime import date, datetime
from pydantic import BaseModel, Field
from pydantic.networks import EmailStr

class addToCartInputs(BaseModel):
    quantity: int