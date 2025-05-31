from decimal import Decimal

from pydantic import BaseModel, Field, PositiveInt, ConfigDict, NonNegativeInt
from typing import Optional, List, Annotated


Money = Annotated[Decimal, Field(ge=0, max_digits=12, decimal_places=2)]


class ProductBase(BaseModel):
    name: Annotated[str, Field(min_length=1, max_length=255)]
    description: Optional[str]
    price: Annotated[float, Field(gt=0)]
    quantity_in_stock: NonNegativeInt
    user_id: PositiveInt


class ProductCreate(BaseModel):
    name: Annotated[str, Field(min_length=1, max_length=255)]
    description: Optional[str]
    price: Annotated[float, Field(gt=0)]
    quantity_in_stock: NonNegativeInt

class ProductUpdate(BaseModel):
    name: Annotated[Optional[str], Field(None, min_length=1, max_length=255)]
    description: Optional[str] = None
    price: Annotated[Optional[float], Field(gt=0)]
    quantity_in_stock: Optional[NonNegativeInt] = None


class ProductRead(ProductBase):
    id: PositiveInt

    model_config = ConfigDict(from_attributes=True,
                              extra="ignore",
                              validate_assignment=True)


class SearchResponse(BaseModel):
    total: int = Field(..., description="Сколько всего документов совпало")
    items: List[ProductRead]