from datetime import datetime, timezone
from typing import List

from fastapi import APIRouter, HTTPException, status, Depends

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


# Endpoints
@router.post(
    "/reviews",
    response_model=ReviewRead,
    status_code=status.HTTP_201_CREATED
)
async def create_review(
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
    return {"id": str(res.inserted_id), **doc}


@router.post(
    "/reviews/{review_id}/reply",
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
        return_document=True,          # вернуть обновлённый документ
    )
    if res is None:
        raise HTTPException(404, "Comment not found")

    return {
        "id": str(res["_id"]),
        **{k: v for k, v in res.items() if k != "_id"},
    }


@router.delete(
    "/reviews/{review_id}/reply/{index}",
    status_code=204,
)
async def delete_reply(
    review_id: str,
    index: int,                              # номер в массиве
    curr=Depends(get_current_user),
    coll=Depends(reviews_collection),
):
    # выбираем только свои ответы или админ
    path = f"replies.{index}.user_id"
    doc = await coll.find_one({"_id": obj_id(review_id), path: curr.user_id})
    if not doc:
        raise HTTPException(404, "Not found or not owner")

    # $unset + $pull, чтобы убрать дырку
    await coll.update_one(
        {"_id": obj_id(review_id)},
        {
            "$unset": {f"replies.{index}": 1},
            "$pull": {"replies": None},
        },
    )


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
    status_code=status.HTTP_204_NO_CONTENT,
)
async def delete_review(
        review_id: str,
        curr: TokenData = Depends(get_current_user),
        coll=Depends(reviews_collection),
):
    # 1. Ищем документ, чтобы узнать автора
    doc = await coll.find_one({"_id": obj_id(review_id)})
    if not doc:
        raise HTTPException(status_code=404, detail="Not found")

    # 2. Разрешаем удалять только автору или администратору
    is_owner = doc["user_id"] == curr.user_id
    if not is_owner:
        raise HTTPException(status_code=403, detail="Forbidden")

    # 3. Удаляем
    await coll.delete_one({"_id": obj_id(review_id)})
