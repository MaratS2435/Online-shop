from pydantic import BaseModel, Field, PositiveInt, EmailStr
from typing import Optional, Annotated
from datetime import datetime

class Reply(BaseModel):
    user_id: PositiveInt
    name: Annotated[str, Field(min_length=1, max_length=100)]
    text: Annotated[str, Field(min_length=1, max_length=500)]
    created_at: datetime

class ReplyCreate(BaseModel):
    text: Annotated[str, Field(min_length=1, max_length=200)]

class ReviewCreate(BaseModel):
    product_id: PositiveInt
    rating: Annotated[int, Field(ge=1, le=5)]
    text: Optional[str] = None

class ReviewRead(ReviewCreate):
    id: str
    user_id: PositiveInt
    name: Annotated[str, Field(min_length=1, max_length=100)]
    created_at: datetime
    replies: list[Reply] = []  # ← добавили

class TokenData(BaseModel):
    user_id: PositiveInt
    name: Annotated[str, Field(min_length=1, max_length=100)]
    email: EmailStr
