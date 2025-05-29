from datetime import datetime, timezone
from typing import List

from fastapi import APIRouter, HTTPException, status, Depends
from app.database import init_indexes
from app.utils.mongo import obj_id
from app.schemas.review import ReviewRead, ReviewCreate
from app.dependencies import reviews_collection

router = APIRouter(
    prefix="/reviews",
    tags=["reviews"],
)

@router.on_event("startup")
async def startup():
    await init_indexes()


# Endpoints
@router.post(
    "/reviews",
    response_model=ReviewRead,
    status_code=status.HTTP_201_CREATED
)
async def create_review(
        data: ReviewCreate,
        coll=Depends(reviews_collection)
):
    doc = data.model_dump()
    doc["created_at"] = datetime.now(timezone.utc)
    res = await coll.insert_one(doc)
    result = {"id": str(res.inserted_id), **doc}
    return result

@router.get(
    "/reviews",
    response_model=List[ReviewRead]
)
async def list_reviews(
        product_id: int | None = None,
        coll=Depends(reviews_collection)
):
    query = {"product_id": product_id} if product_id else {}
    cursor = coll.find(query)
    items = [
        {"id": str(d["_id"]), **{k: v for k, v in d.items() if k != "_id"}}
        async for d in cursor
    ]
    return items

@router.delete(
    "/reviews/{review_id}",
    status_code=status.HTTP_204_NO_CONTENT
)
async def delete_review(
        review_id: str,
        coll=Depends(reviews_collection)
):
    res = await coll.delete_one({"_id": obj_id(review_id)})
    if res.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Not found")
    return None