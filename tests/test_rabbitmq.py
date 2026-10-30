import asyncio
import logging

import aio_pika

from app.config.settings import settings


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
)


async def test_rabbitmq():
    print("\n>>> Starting RabbitMQ test")

    print(
        f">>> RabbitMQ URL: {settings.rabbitmq_url}"
    )

    connection = None

    try:
        # Connect
        connection = await aio_pika.connect_robust(
            settings.rabbitmq_url,
            timeout=10,
        )

        print(">>> RabbitMQ connection: SUCCESS")

        # Create channel
        channel = await connection.channel()

        print(">>> RabbitMQ channel: SUCCESS")

        # Declare queue
        queue = await channel.declare_queue(
            settings.rabbitmq_scoring_queue,
            durable=True,
        )

        print(
            f">>> RabbitMQ queue: SUCCESS "
            f"({queue.name})"
        )

        # Publish test message
        message = aio_pika.Message(
            body=b'{"test": "rabbitmq"}',
            content_type="application/json",
            delivery_mode=aio_pika.DeliveryMode.PERSISTENT,
        )

        await channel.default_exchange.publish(
            message,
            routing_key=settings.rabbitmq_scoring_queue,
        )

        print(">>> RabbitMQ publish: SUCCESS")

        print("\n>>> ALL RABBITMQ TESTS PASSED")

    except Exception as exc:
        print("\n>>> RABBITMQ TEST FAILED")
        print(f">>> Error: {exc}")

        logging.exception(
            "RabbitMQ test failed"
        )

    finally:
        if connection:
            await connection.close()
            print(">>> RabbitMQ connection closed")


if __name__ == "__main__":
    asyncio.run(test_rabbitmq())