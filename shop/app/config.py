from dotenv import load_dotenv
import os

load_dotenv()


class Settings:
    POSTGRES_URL=os.getenv("POSTGRES_URL")

    OPENSEARCH_URL=os.getenv("OPENSEARCH_URL", "http://opensearch:9200")
    OPENSEARCH_HOST=os.getenv("OPENSEARCH_HOST")
    OPENSEARCH_PORT=os.getenv("OPENSEARCH_PORT")
    OPENSEARCH_USE_SSL=os.getenv("OPENSEARCH_USE_SSL")
    OPENSEARCH_VERIFY_CERTS=os.getenv("OPENSEARCH_VERIFY_CERTS")
    OPENSEARCH_INDEX=os.getenv("OPENSEARCH_INDEX")

    JWT_SECRET=os.getenv("JWT_SECRET", "secret")
    JWT_ALGORITHM=os.getenv("JWT_ALGORITHM", "HS256")
    ACCESS_TOKEN_EXPIRE_MINUTES=os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", 30)

    KAFKA_BOOTSTRAP=os.getenv("KAFKA_BOOTSTRAP", "kafka:9092")

    MONGO_URL = os.getenv("MONGO_URL", "mongodb://mongo:27017")
    MONGO_DB = os.getenv("MONGO_DB", "shop")

    REDIS_URL = os.getenv("REDIS_URL", "redis://redis:6379")
    TTL = os.getenv("TTL", 300)