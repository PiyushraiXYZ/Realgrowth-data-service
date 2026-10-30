import json
import logging

import aio_pika
from aio_pika import DeliveryMode, Message

from app.config.settings import settings


logger = logging.getLogger(__name__)


class RabbitMQProducer:

    def __init__(self):
        self.connection = None
        self.channel = None

    async def connect(self):
        try:
            logger.info(
                "Connecting to RabbitMQ | url=%s",
                settings.rabbitmq_url,
            )

            self.connection = await aio_pika.connect_robust(
                settings.rabbitmq_url,
                timeout=10,
            )

            logger.info("RabbitMQ connection established")

            self.channel = await self.connection.channel(
                publisher_confirms=True
            )

            logger.info("RabbitMQ channel created")

            await self.channel.declare_queue(
                settings.rabbitmq_scoring_queue,
                durable=True,
            )

            logger.info(
                "RabbitMQ connected | queue=%s",
                settings.rabbitmq_scoring_queue,
            )

        except Exception:
            logger.exception("RabbitMQ connection failed")
            raise

    async def publish_scoring_job(
        self,
        prospect_id: str,
        provider: str,
    ):
        if not self.channel:
            raise RuntimeError(
                "RabbitMQ producer is not connected"
            )

        payload = {
            "event": "prospect.scoring.requested",
            "prospect_id": prospect_id,
            "provider": provider,
            "attempt": 0,
        }

        message = Message(
            body=json.dumps(payload).encode("utf-8"),
            content_type="application/json",
            delivery_mode=DeliveryMode.PERSISTENT,
        )

        await self.channel.default_exchange.publish(
            message,
            routing_key=settings.rabbitmq_scoring_queue,
        )

        logger.info(
            "Scoring job published | prospect_id=%s | provider=%s",
            prospect_id,
            provider,
        )

    async def close(self):
        if self.connection:
            await self.connection.close()

        self.connection = None
        self.channel = None

        logger.info("RabbitMQ connection closed")


# =========================================================
# SHARED RABBITMQ PRODUCER
# =========================================================

rabbitmq_producer = RabbitMQProducer()