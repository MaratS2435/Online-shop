import logging
from enum import Enum
from datetime import datetime, timezone

from fastapi import FastAPI, status
from pydantic import BaseModel, Field, PositiveInt

from app.kafka import kafka_producer

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("activity-collector")

app = FastAPI(title="Activity Collector", version="0.1.0")

class Action(str, Enum):
    view = "view"
    buy = "buy"
    cart = "cart"

class TrackEvent(BaseModel):
    product_id: PositiveInt
    user_id: PositiveInt
    action: Action = Field(..., description="Тип действия: view/buy/cart")
    ts: datetime | None = None  # если клиент не прислал, поставим now()

@app.on_event("startup")
async def startup():
    await kafka_producer.start()

@app.on_event("shutdown")
async def shutdown():
    await kafka_producer.stop()

@app.post("/track", status_code=status.HTTP_202_ACCEPTED)
async def track(event: TrackEvent):
    if event.ts is None:
        event.ts = datetime.now(timezone.utc)
    await kafka_producer.send(event.model_dump())
    return {"status": "queued"}