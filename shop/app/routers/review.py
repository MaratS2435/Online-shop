import uuid
from datetime import datetime, timezone
from typing import List

from fastapi import APIRouter, HTTPException, status, Depends, Request

from app.database import init_indexes
from app.utils.mongo import obj_id
from app.schemas.review import ReviewRead, ReviewCreate, TokenData, ReplyCreate
from app.dependencies import reviews_collection, get_current_user



router = APIRouter(
    prefix="/reviews",
    tags=["reviews"],
    dependencies=[Depends(get_current_user)]
)

@router.on_event("startup")
async def startup():
    await init_indexes()


@router.post(
    "/",
    response_model=ReviewRead,
    status_code=status.HTTP_201_CREATED
)
async def create_review(
        request: Request,
        data: ReviewCreate,
        current_user: TokenData = Depends(get_current_user),
        coll=Depends(reviews_collection)
):
    doc = data.model_dump()
    doc.update(
        {
            "user_id": current_user.user_id,
            "name": current_user.name,
            "created_at": datetime.now(timezone.utc),
            "replies": [],
        }
    )
    res = await coll.insert_one(doc)

    event_id = str(uuid.uuid4())
    event = {
        "id": str(res.inserted_id),
        "text": doc["text"],
        "product_id": doc["product_id"],
    }
    await request.app.state.producer.send(
        "review-created",
        key=event_id.encode(),
        value=event
    )

    return {"id": str(res.inserted_id), **doc}


@router.post(
    "/{review_id}/reply/",
    response_model=ReviewRead,
    status_code=201,
)
async def add_reply(
    review_id: str,
    data: ReplyCreate,
    current_user: TokenData = Depends(get_current_user),
    coll=Depends(reviews_collection),
):
    reply = {
        "user_id": current_user.user_id,
        "name": current_user.name,
        "text": data.text,
        "created_at": datetime.now(timezone.utc),
    }

    res = await coll.find_one_and_update(
        {"_id": obj_id(review_id)},
        {"$push": {"replies": reply}},
        return_document=True,
    )
    if res is None:
        raise HTTPException(404, "Comment not found")

    return {
        "id": str(res["_id"]),
        **{k: v for k, v in res.items() if k != "_id"},
    }


@router.delete(
    "/{review_id}/reply/{index}/",
    status_code=204,
)
async def delete_reply(
    review_id: str,
    index: int,
    curr=Depends(get_current_user),
    coll=Depends(reviews_collection),
):
    path = f"replies.{index}.user_id"
    doc = await coll.find_one({"_id": obj_id(review_id), path: curr.user_id})
    if not doc:
        raise HTTPException(404, "Not found or not owner")

    await coll.update_one(
        {"_id": obj_id(review_id)},
        {
            "$unset": {f"replies.{index}": 1},
            "$pull": {"replies": None},
        },
    )


@router.get(
    "/",
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
    "/{review_id}/",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def delete_review(
        review_id: str,
        curr: TokenData = Depends(get_current_user),
        coll=Depends(reviews_collection),
):
    doc = await coll.find_one({"_id": obj_id(review_id)})
    if not doc:
        raise HTTPException(status_code=404, detail="Not found")

    is_owner = doc["user_id"] == curr.user_id
    if not is_owner:
        raise HTTPException(status_code=403, detail="Forbidden")

    await coll.delete_one({"_id": obj_id(review_id)})
