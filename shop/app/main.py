import json
import logging
import uuid
from datetime import datetime, timezone

import jwt
from fastapi import FastAPI, Request
from opensearchpy import AsyncOpenSearch

from aiokafka import AIOKafkaProducer

from app.config import Settings
from app.routers import product, auth, review, transactions
from app.database import init_db

from prometheus_fastapi_instrumentator import Instrumentator

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("product-service")

TOPIC = "raw-events"
app = FastAPI(title="Online Shop", version="0.1.0")
producer: AIOKafkaProducer | None = None
Instrumentator().instrument(app).expose(app)

app.include_router(product.router)
app.include_router(auth.router)
app.include_router(review.router)

app.include_router(transactions.router)

# oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login/")

@app.on_event("startup")
async def startup_event():
    app.state.os_client = AsyncOpenSearch(
        hosts=[{"host": "opensearch", "port": 9200}],
        use_ssl=False,
        verify_certs=False,
    )
    producer = AIOKafkaProducer(
        bootstrap_servers=Settings.KAFKA_BOOTSTRAP,
        value_serializer=lambda v: json.dumps(v).encode()
    )
    await producer.start()
    app.state.producer = producer
    await init_db()


@app.on_event("shutdown")
async def shutdown_event():
    await app.state.producer.stop()
    await app.state.os_client.close()


@app.middleware("http")
async def user_activity(request: Request, call_next):
    try:
        token = await auth.oauth2_scheme(request)
        payload = jwt.decode(token, Settings.JWT_SECRET, algorithms=["HS256"])
        user_id = payload["user_id"]
    except Exception:
        user_id = "anon"

    response = await call_next(request)

    if app.state.producer:
        event_id = str(uuid.uuid4())
        event = {
            "event_id": event_id,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "user_id": user_id,
            "method": request.method,
            "path": request.url.path,
            "status": response.status_code,
        }
        await app.state.producer.send(
            TOPIC,
            key=event_id.encode(),
            value=event
        )
    return response
