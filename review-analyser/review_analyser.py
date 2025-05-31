import asyncio, json, os, logging, re
from datetime import datetime, timezone
from aiokafka import AIOKafkaConsumer
from prometheus_client import Counter, Summary, start_http_server
from transformers import pipeline
from opensearchpy import AsyncOpenSearch
from motor.motor_asyncio import AsyncIOMotorClient
from bson import ObjectId


BOOTSTRAP = os.getenv("KAFKA_BOOTSTRAP", "kafka:9092")
TOPIC      = os.getenv("KAFKA_TOPIC", "review-created")
TARGET     = os.getenv("TARGET", "os")


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
)
log = logging.getLogger("review-analyser")


PROCESSED = Counter("ra_processed_total",   "Reviews analysed")
FAILED    = Counter("ra_failed_total",      "Reviews failed")
LATENCY   = Summary ("ra_latency_seconds",  "Inference latency")

start_http_server(int(os.getenv("PROM_PORT", 8000)))

log.info("Loading models … this may take ~20s on first run")
sentiment_pipe = pipeline(
    "sentiment-analysis",
    model="cardiffnlp/twitter-roberta-base-sentiment-latest",
    truncation=True,
    batch_size=32,
)
toxic_pipe = pipeline(
    "text-classification",
    model="textdetox/xlmr-large-toxicity-classifier-v2",
    truncation=True,
    batch_size=32,
)

os_client = AsyncOpenSearch(
    hosts=[{"host": os.getenv("OS_HOST", "opensearch"),
            "port": int(os.getenv("OS_PORT", 9200))}],
    use_ssl=False, verify_certs=False,
)

async def save_enriched(doc: dict):
    await os_client.update(
        index="reviews",
        id=doc["id"],
        body={"doc": doc, "doc_as_upsert": True},
    )

async def run():
    consumer = AIOKafkaConsumer(
        TOPIC,
        bootstrap_servers=BOOTSTRAP,
        value_deserializer=lambda b: json.loads(b.decode()),
        enable_auto_commit=True,
        auto_offset_reset="earliest",
    )
    await consumer.start()
    log.info("Started, waiting for messages…")

    try:
        async for msg in consumer:
            log.info("got message %s", msg.value)
            data = msg.value
            text = data["text"]

            with LATENCY.time():
                loop = asyncio.get_running_loop()
                LABEL_MAP = {"LABEL_0": "negative", "LABEL_1": "neutral", "LABEL_2": "positive"}

                def normalize_sent(pred_label: str) -> str:
                    if pred_label in LABEL_MAP:
                        return LABEL_MAP[pred_label]
                    return pred_label.lower()

                sent_predict = loop.run_in_executor(
                    None,
                    lambda: normalize_sent(sentiment_pipe(text)[0]["label"])
                )

                tox_predict = loop.run_in_executor(
                    None,
                    lambda: toxic_pipe(text)[0]["label"] == "toxic",
                )

                sent, toxic = await asyncio.gather(sent_predict, tox_predict)

            enriched = {
                "id": data["id"],
                "sentiment": sent,
                "toxic": toxic,
                "analysed_at": datetime.now(timezone.utc).isoformat(),
            }
            await save_enriched(enriched)
            log.info("processed %s", enriched)
            PROCESSED.inc()
    except Exception as e:
        FAILED.inc()
        log.exception("Error in loop: %s", e)
    finally:
        await consumer.stop()

if __name__ == "__main__":
    asyncio.run(run())
