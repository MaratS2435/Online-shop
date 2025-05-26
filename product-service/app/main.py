import asyncio
import logging
from typing import List

from fastapi import FastAPI, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, delete

from app.database import async_session, init_db
from app import models, schemas
from app.kafka import kafka_producer

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
logger = logging.getLogger("product-service")

app = FastAPI(title="Product Service", version="0.1.0")
Instrumentator().instrument(app).expose(app)  # /metrics

async def get_session() -> AsyncSession:
    async with async_session() as session:
        yield session


@app.on_event("startup")
async def startup_event():
    await init_db()
    await kafka_producer.start()


@app.on_event("shutdown")
async def shutdown_event():
    await kafka_producer.stop()


# -------- Seller endpoints --------
@app.post("/sellers", response_model=schemas.SellerRead, status_code=status.HTTP_201_CREATED)
async def create_seller(data: schemas.SellerCreate, session: AsyncSession = Depends(get_session)):
    with tracer.start_as_current_span("create_seller"):
        seller = models.Seller(**data.model_dump())
        session.add(seller)
        await session.commit()
        await session.refresh(seller)
        return seller


@app.get("/sellers", response_model=List[schemas.SellerRead])
async def list_sellers(session: AsyncSession = Depends(get_session)):
    with tracer.start_as_current_span("list_sellers"):
        result = await session.execute(select(models.Seller))
        return result.scalars().all()


# -------- Product endpoints --------
@app.post("/products", response_model=schemas.ProductRead, status_code=status.HTTP_201_CREATED)
async def create_product(data: schemas.ProductCreate, session: AsyncSession = Depends(get_session)):
    with tracer.start_as_current_span("create_product"):
        product = models.Product(**data.model_dump())
        session.add(product)
        await session.commit()
        await session.refresh(product)
        await kafka_producer.send({"action": "created", "product": schemas.ProductRead.model_validate(product).model_dump()})
        return product


@app.get("/products", response_model=List[schemas.ProductRead])
async def list_products(session: AsyncSession = Depends(get_session)):
    with tracer.start_as_current_span("list_products"):
        result = await session.execute(select(models.Product))
        return result.scalars().all()


@app.get("/products/{product_id}", response_model=schemas.ProductRead)
async def get_product(product_id: int, session: AsyncSession = Depends(get_session)):
    with tracer.start_as_current_span("get_product"):
        result = await session.execute(select(models.Product).where(models.Product.id == product_id))
        product = result.scalar_one_or_none()
        if not product:
            raise HTTPException(status_code=404, detail="Product not found")
        return product


@app.put("/products/{product_id}", response_model=schemas.ProductRead)
async def update_product(product_id: int, data: schemas.ProductUpdate, session: AsyncSession = Depends(get_session)):
    with tracer.start_as_current_span("get_product"):
        result = await session.execute(select(models.Product).where(models.Product.id == product_id))
        product = result.scalar_one_or_none()
        if not product:
            raise HTTPException(status_code=404, detail="Product not found")

        for key, value in data.model_dump(exclude_unset=True).items():
            setattr(product, key, value)

        await session.commit()
        await session.refresh(product)
        await kafka_producer.send({"action": "updated", "product": schemas.ProductRead.model_validate(product).model_dump()})
        return product


@app.delete("/products/{product_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_product(product_id: int, session: AsyncSession = Depends(get_session)):
    result = await session.execute(select(models.Product).where(models.Product.id == product_id))
    product = result.scalar_one_or_none()
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    await session.delete(product)
    await session.commit()
    await kafka_producer.send({"action": "deleted", "product_id": product_id})
    return None