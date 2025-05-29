from bson import ObjectId
from fastapi import HTTPException


def obj_id(id: str) -> ObjectId:
    try:
        return ObjectId(id)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid ID")