import json, os, asyncio, logging
from aiokafka import AIOKafkaProducer

logger = logging.getLogger(__name__)

KAFKA_BOOTSTRAP = os.getenv("KAFKA_BOOTSTRAP", "localhost:29092")
TOPIC_PRODUCTS = "products"


class KafkaProducer:
    _producer: AIOKafkaProducer | None = None

    async def start(self):
        if self._producer is None:
            self._producer = AIOKafkaProducer(bootstrap_servers=KAFKA_BOOTSTRAP)
            await self._producer.start()
            logger.info("Kafka producer started")

    async def send(self, event: dict):
        if self._producer is None:
            await self.start()
        payload = json.dumps(event, default=str).encode()
        await self._producer.send_and_wait(TOPIC_PRODUCTS, payload)
        logger.debug("Sent event to Kafka: %s", payload)

    async def stop(self):
        if self._producer:
            await self._producer.stop()
            self._producer = None
            logger.info("Kafka producer stopped")

kafka_producer = KafkaProducer()