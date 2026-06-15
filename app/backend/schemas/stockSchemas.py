from datetime import date, datetime
from pydantic import BaseModel, Field
from pydantic.networks import EmailStr


class stock_inputs(BaseModel):
    product_id: int
    sku_id: str
    price: float = Field(..., gt=0)
    quantity: int = Field(..., ge=0)


class stock_update_inputs(BaseModel):
    sku_id: str | None = None
    price: float | None = Field(None, gt=0)
    quantity: int | None = Field(None, ge=0)