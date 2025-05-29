import logging

from fastapi import FastAPI
from fastapi.security import OAuth2PasswordBearer
from opensearchpy import AsyncOpenSearch

from app.routers import product_sellers, auth, review
from app.database import init_db

from prometheus_fastapi_instrumentator import Instrumentator

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("product-service")

app = FastAPI(title="Online Shop", version="0.1.0")
Instrumentator().instrument(app).expose(app)  # /metrics

app.include_router(product_sellers.router)
app.include_router(auth.router)
app.include_router(review.router)

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login/")

@app.on_event("startup")
async def startup_event():
    app.state.os_client = AsyncOpenSearch(
        hosts=[{"host": "opensearch", "port": 9200}],
        use_ssl=False,
        verify_certs=False,
    )
    await init_db()


@app.on_event("shutdown")
async def shutdown_event():
    await app.state.os_client.close()
