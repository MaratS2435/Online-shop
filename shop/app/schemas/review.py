from pydantic import BaseModel, Field, PositiveInt
from typing import Optional, Annotated
from datetime import datetime

class ReviewCreate(BaseModel):
    product_id: PositiveInt
    author: Annotated[str, Field(min_length=1, max_length=100)]
    rating: Annotated[int, Field(ge=1, le=5)]
    text: Optional[str] = None

class ReviewRead(ReviewCreate):
    id: str
    created_at: datetime