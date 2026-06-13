from pydantic import BaseModel, ConfigDict
from typing import Optional

class ProductResponse(BaseModel):
    id: int
    name: str
    summary: str
    description: str

    category: Optional[str] = None
    subcategory: Optional[str] = None
    cover_image_url: Optional[str] = None

    model_config = ConfigDict(
        from_attributes=True
    )