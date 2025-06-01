from typing import List

from fastapi import APIRouter, Depends, HTTPException, status, Query, Path, Request
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.dependencies import get_current_user
from app.database import get_session
from app.config import Settings
from app.models.product import Product
from app.schemas.product import (
    ProductRead, ProductCreate, ProductUpdate,
    SearchResponse,
)
from app.schemas.review import TokenData


router = APIRouter(
    prefix="/products-sellers",
    tags=["products-sellers"],
)


@router.post(
    "/products",
    response_model=ProductRead,
    status_code=status.HTTP_201_CREATED
)
async def create_product(
        data: ProductCreate,
        current_user: TokenData = Depends(get_current_user),
        session: AsyncSession = Depends(get_session)
):
    doc = data.model_dump()
    doc["user_id"] = current_user.user_id

    product = Product(**doc)

    session.add(product)
    await session.commit()
    await session.refresh(product)


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
    current_user: TokenData = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    product = await session.scalar(select(Product).where(Product.id == product_id))
    if product is None:
        raise HTTPException(status_code=404, detail="Product not found")

    if product.user_id != current_user.user_id:
        raise HTTPException(status_code=403, detail="Forbidden")



    data = payload.model_dump(exclude_unset=True)
    if not data:
        return product

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
    current_user: TokenData = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    product = await session.scalar(select(Product).where(Product.id == product_id))
    if product is None:
        raise HTTPException(status_code=404, detail="Product not found")

    if product.user_id != current_user.user_id:
        raise HTTPException(status_code=403, detail="Forbidden")

    await session.delete(product)
    await session.commit()