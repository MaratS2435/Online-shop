import logging
from datetime import datetime
from typing import List

from fastapi import FastAPI, HTTPException, status, Depends
from bson import ObjectId
from app.database import get_db, init_indexes
from app import schemas
from app.kafka import kafka

from opentelemetry import trace
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.sdk.resources import SERVICE_NAME, Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor

from prometheus_fastapi_instrumentator import Instrumentator

resource = Resource(attributes={SERVICE_NAME: "product-service"})
provider = TracerProvider(resource=resource)
processor = BatchSpanProcessor(OTLPSpanExporter(endpoint="otel-collector:4317", insecure=True))
provider.add_span_processor(processor)
trace.set_tracer_provider(provider)

tracer = trace.get_tracer(__name__)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("review-service")

app = FastAPI(title="Review Service", version="0.1.0")
Instrumentator().instrument(app).expose(app)  # /metrics

@app.on_event("startup")
async def startup():
    await init_indexes()
    await kafka.start()

@app.on_event("shutdown")
async def shutdown():
    await kafka.stop()

# Dependency
async def reviews_collection():
    db = get_db()
    yield db.reviews

# Helpers

def obj_id(id: str) -> ObjectId:
    try:
        return ObjectId(id)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid ID")

# Endpoints
@app.post("/reviews", response_model=schemas.ReviewRead, status_code=status.HTTP_201_CREATED)
async def create_review(data: schemas.ReviewCreate, coll=Depends(reviews_collection)):
    with tracer.start_as_current_span("create_review"):
        doc = data.model_dump()
        doc["created_at"] = datetime.utcnow()
        res = await coll.insert_one(doc)
        result = {"id": str(res.inserted_id), **doc}
        await kafka.send({"action": "created", "review": result})
        return result

@app.get("/reviews", response_model=List[schemas.ReviewRead])
async def list_reviews(product_id: int | None = None, coll=Depends(reviews_collection)):
    with tracer.start_as_current_span("list_reviews"):
        query = {"product_id": product_id} if product_id else {}
        cursor = coll.find(query)
        items = [
            {"id": str(d["_id"]), **{k: v for k, v in d.items() if k != "_id"}}
            async for d in cursor
        ]
        return items

@app.delete("/reviews/{review_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_review(review_id: str, coll=Depends(reviews_collection)):
    with tracer.start_as_current_span("delete_review"):
        res = await coll.delete_one({"_id": obj_id(review_id)})
        if res.deleted_count == 0:
            raise HTTPException(status_code=404, detail="Not found")
        await kafka.send({"action": "deleted", "review_id": review_id})
        return None