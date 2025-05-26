from pydantic import BaseModel, Field, PositiveInt, ConfigDict
from typing import Optional


class SellerCreate(BaseModel):
    name: str = Field(min_length=1, max_length=255)


class SellerRead(SellerCreate):
    id: PositiveInt

    model_config = ConfigDict(from_attributes=True)


class ProductBase(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    description: Optional[str] = None
    price: float = Field(gt=0)
    in_stock: bool = True
    seller_id: PositiveInt


class ProductCreate(ProductBase):
    pass


class ProductUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = None
    price: Optional[float] = Field(None, gt=0)
    in_stock: Optional[bool] = None


class ProductRead(ProductBase):
    id: PositiveInt
    model_config = ConfigDict(from_attributes=True)