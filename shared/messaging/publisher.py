"""
Message publisher for RabbitMQ.
"""

import json
from typing import Any

from aio_pika import DeliveryMode, Message

from shared.config.logging import get_logger
from shared.exceptions import MessagePublishError
from shared.messaging.queues import QueueConfig
from shared.messaging.rabbitmq_client import RabbitMQClient

logger = get_logger(__name__)


class MessagePublisher:
    """Message publisher for RabbitMQ queues."""

    def __init__(self, client: RabbitMQClient):
        """
        Initialize message publisher.

        Args:
            client: RabbitMQ client instance
        """
        self.client = client

    async def publish(
        self,
        queue_config: QueueConfig,
        message: dict[str, Any],
        priority: int = 0,
        persistent: bool = True,
        correlation_id: str | None = None,
        reply_to: str | None = None,
    ) -> None:
        """
        Publish a message to a queue.

        Args:
            queue_config: Queue configuration
            message: Message payload (will be JSON serialized)
            priority: Message priority (0-9, higher is more important)
            persistent: Whether message survives broker restart
            correlation_id: Correlation ID for request-response pattern
            reply_to: Reply queue for request-response pattern

        Raises:
            MessagePublishError: If publishing fails
        """
        try:
            # Serialize message
            body = json.dumps(message).encode()

            # Create message
            msg = Message(
                body=body,
                delivery_mode=(
                    DeliveryMode.PERSISTENT if persistent else DeliveryMode.NOT_PERSISTENT
                ),
                priority=priority,
                correlation_id=correlation_id,
                reply_to=reply_to,
                content_type="application/json",
            )

            # Get exchange
            if queue_config.exchange:
                exchange = await self.client.declare_exchange(queue_config.exchange)
                routing_key = queue_config.routing_key or queue_config.name

                # Publish to exchange
                await exchange.publish(msg, routing_key=routing_key)

                logger.debug(
                    "message_published",
                    exchange=queue_config.exchange,
                    routing_key=routing_key,
                    correlation_id=correlation_id,
                )
            else:
                # Publish directly to queue
                channel = self.client.get_channel()
                await channel.default_exchange.publish(
                    msg,
                    routing_key=queue_config.name,
                )

                logger.debug(
                    "message_published",
                    queue=queue_config.name,
                    correlation_id=correlation_id,
                )

        except Exception as e:
            logger.error(
                "message_publish_failed",
                queue=queue_config.name,
                error=str(e),
            )
            raise MessagePublishError(
                queue=queue_config.name,
                message=f"Failed to publish message: {e}",
            ) from e

    async def publish_batch(
        self,
        queue_config: QueueConfig,
        messages: list[dict[str, Any]],
        priority: int = 0,
        persistent: bool = True,
    ) -> None:
        """
        Publish multiple messages to a queue.

        Args:
            queue_config: Queue configuration
            messages: List of message payloads
            priority: Message priority (0-9)
            persistent: Whether messages survive broker restart

        Raises:
            MessagePublishError: If publishing fails
        """
        try:
            for message in messages:
                await self.publish(
                    queue_config=queue_config,
                    message=message,
                    priority=priority,
                    persistent=persistent,
                )

            logger.info(
                "batch_published",
                queue=queue_config.name,
                count=len(messages),
            )

        except Exception as e:
            logger.error(
                "batch_publish_failed",
                queue=queue_config.name,
                error=str(e),
            )
            raise MessagePublishError(
                queue=queue_config.name,
                message=f"Failed to publish batch: {e}",
            ) from e

    async def publish_with_reply(
        self,
        queue_config: QueueConfig,
        message: dict[str, Any],
        reply_queue: str,
        timeout: float = 30.0,
    ) -> dict[str, Any]:
        """
        Publish a message and wait for reply (RPC pattern).

        Args:
            queue_config: Queue configuration
            message: Message payload
            reply_queue: Queue to receive reply on
            timeout: Timeout in seconds

        Returns:
            Reply message payload

        Raises:
            MessagePublishError: If publishing fails
            TimeoutError: If reply not received in time
        """
        import asyncio
        import uuid

        try:
            correlation_id = str(uuid.uuid4())
            reply_future: asyncio.Future = asyncio.Future()

            # Set up reply consumer
            channel = self.client.get_channel()
            reply_queue_obj = await channel.declare_queue(reply_queue, exclusive=True)

            async def on_reply(msg: Any) -> None:
                if msg.correlation_id == correlation_id:
                    reply_data = json.loads(msg.body.decode())
                    reply_future.set_result(reply_data)
                    await msg.ack()

            await reply_queue_obj.consume(on_reply)

            # Publish request
            await self.publish(
                queue_config=queue_config,
                message=message,
                correlation_id=correlation_id,
                reply_to=reply_queue,
            )

            # Wait for reply
            reply = await asyncio.wait_for(reply_future, timeout=timeout)

            logger.debug(
                "rpc_reply_received",
                correlation_id=correlation_id,
            )

            return reply

        except TimeoutError as timeout_err:
            logger.error(
                "rpc_timeout",
                queue=queue_config.name,
                correlation_id=correlation_id,
            )
            raise TimeoutError(f"RPC timeout after {timeout}s") from timeout_err

        except Exception as e:
            logger.error(
                "rpc_failed",
                queue=queue_config.name,
                error=str(e),
            )
            raise MessagePublishError(
                queue=queue_config.name,
                message=f"RPC failed: {e}",
            ) from e
