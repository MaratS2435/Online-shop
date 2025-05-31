from pydantic import BaseModel, Field, PositiveInt
from decimal import Decimal
from datetime import datetime

class DepositCreate(BaseModel):
    amount: Decimal = Field(..., gt=0, max_digits=12, decimal_places=2)


class PurchaseCreate(BaseModel):
    quantity: PositiveInt
    product_id: PositiveInt


class TransactionRead(BaseModel):
    id: PositiveInt
    user_id: PositiveInt
    amount: Decimal
    type: str
    product_id: PositiveInt | None
    created_at: datetime

    model_config = {"from_attributes": True}