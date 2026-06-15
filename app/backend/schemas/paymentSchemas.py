from datetime import date, datetime
from pydantic import BaseModel, Field
from pydantic.networks import EmailStr


class payment_create_inputs(BaseModel):
    order_id: int
    payment_method: str

class payment_verify_inputs(BaseModel):
    payment_reference: str