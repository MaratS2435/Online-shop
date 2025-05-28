from pydantic import BaseModel, Field, PositiveInt, ConfigDict, NonNegativeInt
from typing import Optional, List


class SellerCreate(BaseModel):
    name: str = Field(min_length=1, max_length=255)


class SellerRead(SellerCreate):
    id: PositiveInt

    model_config = ConfigDict(from_attributes=True)


class ProductBase(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    description: Optional[str] = None
    price: float = Field(gt=0)
    quantity_in_stock: NonNegativeInt
    seller_id: PositiveInt


class ProductCreate(ProductBase):
    pass


class ProductUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = None
    price: Optional[float] = Field(None, gt=0)
    quantity_in_stock: Optional[NonNegativeInt] = None


class ProductRead(ProductBase):
    id: PositiveInt
    model_config = ConfigDict(from_attributes=True, extra="ignore")


class SearchResponse(BaseModel):
    total: int = Field(..., description="Сколько всего документов совпало")
    items: List[ProductRead]