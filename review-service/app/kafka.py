import os, json, logging
from aiokafka import AIOKafkaProducer

KAFKA_BOOTSTRAP = os.getenv("KAFKA_BOOTSTRAP", "kafka:9092")
TOPIC_REVIEWS = "reviews"
logger = logging.getLogger(__name__)

class KafkaProducer:
    _producer: AIOKafkaProducer | None = None

    async def start(self):
        if self._producer is None:
            self._producer = AIOKafkaProducer(bootstrap_servers=KAFKA_BOOTSTRAP)
            await self._producer.start()

    async def send(self, event: dict):
        if self._producer is None:
            await self.start()
        await self._producer.send_and_wait(TOPIC_REVIEWS, json.dumps(event, default=str).encode())

    async def stop(self):
        if self._producer:
            await self._producer.stop()
            self._producer = None

kafka = KafkaProducer()
