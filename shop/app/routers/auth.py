import asyncio
from decimal import Decimal

import bcrypt
import jwt
from typing import Annotated, Optional

from fastapi import (
    APIRouter, Depends, HTTPException, Response, status, Cookie
)
from fastapi.security import OAuth2PasswordRequestForm, OAuth2PasswordBearer
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_session
from app.config import Settings
from app.models.auth import User
from app.schemas.auth import UserCreate, UserRead
from app.utils.tokens import create_tokens


router = APIRouter(
    prefix="/auth",       # общий префикс URL
    tags=["auth"],        # метка для OpenAPI-документации
)

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login/")

@router.get("/health")
async def health():
    return {"status": "ok"}


@router.post(
    "/register/",
    response_model=UserRead,
    status_code=status.HTTP_201_CREATED,
)
async def register(
    data: UserCreate,
    session: AsyncSession = Depends(get_session),
):
    # 1. Проверяем дубликат (необязательно, но уменьшает шум в логах)
    if await session.scalar(select(User).filter_by(email=data.email)):
        raise HTTPException(status_code=409, detail="Email already registered")

    # 2. Хешируем пароль в thread-pool
    hashed = await asyncio.to_thread(
        bcrypt.hashpw,
        data.password.get_secret_value().encode(),
        bcrypt.gensalt(),
    )
    hashed = hashed.decode()

    # 3. Создаём ORM-объект
    user = User(
        **data.model_dump(exclude={'password'}),
        password_hash=hashed,
        balance=Decimal("0.00"),  # или 0.0
    )

    # 4. Пишем в БД
    session.add(user)
    try:
        await session.commit()
    except IntegrityError:
        existing = await session.scalar(select(User).filter_by(email=data.email.lower()))
        print("EXISTING:", existing)  # временно
        # перехват гонки unique
        await session.rollback()
        raise HTTPException(status_code=409, detail="Email already registered")

    await session.refresh(user)         # получаем id и прочие дефолты
    return user


@router.post("/login/")
async def login(
    response: Response,
    user_input: OAuth2PasswordRequestForm = Depends(),
    session: AsyncSession = Depends(get_session),
):
    # 1) ищем пользователя
    user = await session.scalar(
        select(User).filter_by(email=user_input.username.lower())
    )
    if user is None:
        raise HTTPException(
            status_code=401,
            detail="Invalid credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # 2) проверяем пароль безопасно для event-loop
    ok = await asyncio.to_thread(
        bcrypt.checkpw,
        user_input.password.encode(),
        user.password_hash.encode(),
    )
    if not ok:
        raise HTTPException(
            status_code=401,
            detail="Invalid credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # 3) генерируем JWT
    access_token, refresh_token = create_tokens(user.email, user.id, user.name)

    # 4) кладём refresh-токен в httpOnly cookie
    response.set_cookie(
        key="refresh_token",
        value=refresh_token,
        httponly=True,
        # secure=settings.COOKIE_SECURE,   # True в проде
        samesite="lax",
        # max_age=settings.REFRESH_TTL,    # желательно указать
        path="/",
    )

    return {"access_token": access_token, "token_type": "bearer"}


@router.post("/refresh/", status_code=200)
async def refresh(
    response: Response,
    refresh_token: Annotated[Optional[str], Cookie()] = None,
):
    if refresh_token is None:
        raise _unauthorized("Refresh token missing")

    try:
        payload = jwt.decode(
            refresh_token,
            Settings.JWT_SECRET,
            algorithms=[Settings.JWT_ALGORITHM],
        )
    except jwt.ExpiredSignatureError:
        raise _unauthorized("Refresh token expired")
    except jwt.PyJWTError:
        raise _unauthorized("Invalid refresh token")

    access_token, _ = create_tokens(payload["email"], payload["user_id"], payload["name"])

    # по желанию: обновляем cookie, чтобы продлить max-age
    response.set_cookie(
        key="refresh_token",
        value=refresh_token,
        httponly=True,
        # secure=Settings.COOKIE_SECURE,
        samesite="lax",
        # max_age=Settings.REFRESH_TTL,
        path="/",
    )
    return {"access_token": access_token, "token_type": "bearer"}


def _unauthorized(msg: str) -> HTTPException:
    return HTTPException(
        status_code=401,
        detail=msg,
        headers={"WWW-Authenticate": "Bearer"},
    )


__all__ = ["router", "oauth2_scheme"]


