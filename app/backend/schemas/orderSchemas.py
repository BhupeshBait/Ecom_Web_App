from datetime import date, datetime
from pydantic import BaseModel, Field
from pydantic.networks import EmailStr


class order_create_inputs(BaseModel):
    address_id: int
    payment_method: str


class order_status_update_inputs(BaseModel):
    status: str
    tracking_number: str | None = None


class order_cancel_inputs(BaseModel):
    reason: str | None = None