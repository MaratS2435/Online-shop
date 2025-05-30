from typing import List

from fastapi import APIRouter, Depends, HTTPException, status, Query, Path, Request
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from opensearchpy import AsyncOpenSearch

from app.dependencies import get_session
from app.routers.auth import oauth2_scheme
from app.config import Settings
from app.models.product_sellers import Product, Seller
from app.schemas.product_sellers import (
    ProductRead, ProductCreate, ProductUpdate,
    SellerRead, SellerCreate, SearchResponse,
    SellerUpdate
)
from app.utils.tokens import create_tokens
from app.kafka import kafka_producer


router = APIRouter(
    prefix="/products-sellers",
    tags=["products-sellers"],
)


# -------- Seller endpoints --------
@router.post(
    "/sellers",
    response_model=SellerRead,
    status_code=status.HTTP_201_CREATED
)
async def create_seller(data: SellerCreate, session: AsyncSession = Depends(get_session)):
    seller = Seller(**data.model_dump())
    session.add(seller)
    await session.commit()
    await session.refresh(seller)
    return seller


@router.get(
    "/sellers/{seller_id}",
    response_model=SellerRead,
    status_code=status.HTTP_200_OK
)
async def get_seller(seller_id: int, session: AsyncSession = Depends(get_session)):
    result = await session.scalar(select(Seller).filter_by(id=seller_id))
    if not result:
        raise HTTPException(status_code=404, detail="Seller not found")
    return result


@router.patch(
    "/sellers/{seller_id}",
    response_model=SellerRead,
    status_code=status.HTTP_200_OK,
)
async def update_seller(
        seller_id: int = Path(..., gt=0),
        payload: SellerUpdate = ...,
        session: AsyncSession = Depends(get_session),
):
    # 1. ищем объект
    seller = await session.scalar(select(Seller).where(Seller.id == seller_id))
    if seller is None:
        raise HTTPException(status_code=404, detail="Seller not found")

    # 2. вытаскиваем только переданные поля
    update_data = payload.model_dump(exclude_unset=True)

    if not update_data:
        return seller  # нечего менять → «idempotent»

    # 3. применяем изменения
    for field, value in update_data.items():
        setattr(seller, field, value)

    await session.commit()
    await session.refresh(seller)  # чтобы получить вычислённые поля/триггеры
    return seller


@router.delete(
    "/sellers/{seller_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def delete_seller(
    seller_id: int = Path(..., gt=0),
    session: AsyncSession = Depends(get_session),
):
    # 1. Пытаемся найти продавца
    seller = await session.scalar(select(Seller).where(Seller.id == seller_id))
    if seller is None:
        raise HTTPException(status_code=404, detail="Seller not found")

    # 2. Удаляем. Если нужны проверки, делаем их ДО delete().
    #    Например: запретить удаление, если у продавца есть товары.
    #    Здесь — простое удаление.
    await session.delete(seller)
    await session.commit()
    # 3. 204 No Content — тело ответа пустое



# -------- Product endpoints --------
@router.post("/products", response_model=ProductRead, status_code=status.HTTP_201_CREATED)
async def create_product(data: ProductCreate, session: AsyncSession = Depends(get_session)):
    product = Product(**data.model_dump())
    session.add(product)
    await session.commit()
    await session.refresh(product)
    # await kafka_producer.send({"action": "created", "product": ProductRead.model_validate(product).model_dump()})
    return product


@router.get(
    "/products",
    response_model=List[ProductRead]
)
async def list_products(session: AsyncSession = Depends(get_session)):
    result = await session.execute(select(Product))
    return result.scalars().all()


@router.get(
    "/products/{product_id}",
    response_model=ProductRead,
    status_code=status.HTTP_200_OK
)
async def get_product(product_id: int, session: AsyncSession = Depends(get_session)):
    result = await session.scalar(select(Product).filter_by(id=product_id))
    if not result:
        raise HTTPException(status_code=404, detail="Product not found")
    return result


@router.get(
    "/products/search/",
    response_model=SearchResponse,
    summary="Поиск товаров"
)
async def search_products(
    request: Request,
    q: str  = Query(..., min_length=2),
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
):
    body = {
        "query": {
            "multi_match": {
                "query": q,
                "fields": ["name", "description"],
                "fuzziness": "AUTO",
            }
        },
        "from": (page - 1) * size,
        "size": size,
    }
    resp = await request.app.state.os_client.search(index=Settings.OPENSEARCH_INDEX, body=body)
    hits  = resp["hits"]["hits"]
    total = resp["hits"]["total"]["value"]
    items = [ProductRead(**h["_source"]) for h in hits]
    return SearchResponse(total=total, items=items)


@router.patch(
    "/products/{product_id}",
    response_model=ProductRead,
    status_code=status.HTTP_200_OK,
)
async def update_product(
    product_id: int = Path(..., gt=0),
    payload: ProductUpdate = ...,
    session: AsyncSession = Depends(get_session),
):
    product = await session.scalar(select(Product).where(Product.id == product_id))
    if product is None:
        raise HTTPException(status_code=404, detail="Product not found")

    data = payload.model_dump(exclude_unset=True)
    if not data:
        return product

    # важное отличие: менять seller_id может быть нельзя
    if "seller_id" in data:
        raise HTTPException(status_code=400, detail="seller_id is immutable")

    for k, v in data.items():
        setattr(product, k, v)

    await session.commit()
    await session.refresh(product)
    return product


@router.delete(
    "/products/{product_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def delete_product(
    product_id: int = Path(..., gt=0),
    session: AsyncSession = Depends(get_session),
):
    product = await session.scalar(select(Product).where(Product.id == product_id))
    if product is None:
        raise HTTPException(status_code=404, detail="Product not found")

    await session.delete(product)
    await session.commit()