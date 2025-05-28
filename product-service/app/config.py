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
