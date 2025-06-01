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
    prefix="/products",
    tags=["products"],
)


@router.post(
    "/",
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
    "/",
    response_model=List[ProductRead]
)
async def list_products(session: AsyncSession = Depends(get_session)):
    result = await session.execute(select(Product))
    return result.scalars().all()


@router.get(
    "/{product_id}/",
    response_model=ProductRead,
    status_code=status.HTTP_200_OK
)
async def get_product(product_id: int, session: AsyncSession = Depends(get_session)):
    result = await session.scalar(select(Product).filter_by(id=product_id))
    if not result:
        raise HTTPException(status_code=404, detail="Product not found")
    return result


@router.get(
    "/search/",
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
    "/{product_id}/",
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
    "/{product_id}/",
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


from fastapi import UploadFile
from datetime import datetime, timezone
import boto3
from botocore.exceptions import ClientError
from app.config import S3_CONFIG


from fastapi import Request

@router.post(
    "/upload/",
    summary="Загрузка CSV-файла в S3",
    status_code=status.HTTP_200_OK
)
async def upload_csv(
    file: UploadFile,
    request: Request,
    current_user: TokenData = Depends(get_current_user)
):
    try:
        user_id = current_user.user_id
        timestamp = datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S")
        file_name = f"{timestamp}_user_{user_id}.csv"

        content = await file.read()

        session = boto3.session.Session()
        s3 = session.client(
            service_name="s3",
            endpoint_url=S3_CONFIG["endpoint_url"],
            aws_access_key_id=S3_CONFIG["aws_access_key_id"],
            aws_secret_access_key=S3_CONFIG["aws_secret_access_key"],
        )

        try:
            s3.head_bucket(Bucket=S3_CONFIG["bucket_name"])
        except ClientError as e:
            error_code = int(e.response['Error']['Code'])
            if error_code == 404:
                s3.create_bucket(Bucket=S3_CONFIG["bucket_name"])
            else:
                raise

        s3.put_object(Bucket=S3_CONFIG["bucket_name"], Key=file_name, Body=content)

        message = {
            "event": "file_uploaded",
            "file_name": file_name,
            "user_id": user_id,
            "timestamp": datetime.utcnow().isoformat()
        }

        producer = request.app.state.producer
        if producer:
            await producer.send_and_wait(
                topic="uploads",
                key=file_name.encode(),
                value=message
            )

        return {"message": "Uploaded to S3 and sent to Kafka", "file": file_name}

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))