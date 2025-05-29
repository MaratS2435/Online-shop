from decimal import Decimal

from pydantic import (
    BaseModel, Field, PositiveInt,
    EmailStr, SecretStr
)
from typing import Optional, List, Annotated

Name     = Annotated[str,       Field(min_length=1, max_length=255)]
Password = Annotated[SecretStr, Field(min_length=8, max_length=128)]
Money    = Annotated[Decimal,   Field(ge=0, max_digits=12, decimal_places=2)]


class UserBase(BaseModel):
    name:  Name
    email: EmailStr


class UserCreate(UserBase):
    password: Password


class UserRead(UserBase):
    id: PositiveInt

    model_config = {
        "from_attributes": True,   # для SQLAlchemy .from_orm()
        "extra": "forbid",         # запрет лишних полей
        "populate_by_name": True,  # если нужны alias-ы
    }


class UserProfile(UserBase):
    id: PositiveInt
    balance: Money


class UserUpdate(BaseModel):
    name:     Optional[Name]     = None
    email:    Optional[EmailStr] = None
    balance:  Optional[Money]    = None
    password: Optional[Password] = None

    model_config = {
        "extra": "forbid",
        "validate_assignment": True,  # чтобы .field = value проходил валидацию
    }


class Token(BaseModel):
    access_token: str
    refresh_token: str