from typing import Annotated

from fastapi import Depends, HTTPException, status, Request
from jose import jwt, JWTError

from app.config import Settings
from app.database import get_db
from app.routers.auth import oauth2_scheme
from app.schemas.review import TokenData


async def reviews_collection():
    db = get_db()
    yield db.reviews


async def get_redis(request: Request):
    return request.app.state.redis


async def get_current_user(
    token: Annotated[str, Depends(oauth2_scheme)]
) -> TokenData:
    credentials_exc = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(
            token,
            Settings.JWT_SECRET,
            algorithms=["HS256"],
        )
        return TokenData(
            user_id=payload["user_id"],
            name=payload["name"],
            email=payload["email"]
        )
    except (JWTError, KeyError):
        raise credentials_exc

