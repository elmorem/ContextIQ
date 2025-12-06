"""
Message consumer for RabbitMQ.
"""

import asyncio
import json
from collections.abc import Callable
from typing import Any

from aio_pika import IncomingMessage

from shared.config.logging import get_logger
from shared.exceptions import MessageConsumeError
from shared.messaging.queues import QueueConfig
from shared.messaging.rabbitmq_client import RabbitMQClient

logger = get_logger(__name__)

MessageHandler = Callable[[dict[str, Any]], Any]


class MessageConsumer:
    """Message consumer for RabbitMQ queues."""

    def __init__(self, client: RabbitMQClient):
        """
        Initialize message consumer.

        Args:
            client: RabbitMQ client instance
        """
        self.client = client
        self._consumers: dict[str, Any] = {}
        self._running = False

    async def consume(
        self,
        queue_config: QueueConfig,
        handler: MessageHandler,
        auto_ack: bool = False,
        prefetch_count: int = 10,
    ) -> None:
        """
        Start consuming messages from a queue.

        Args:
            queue_config: Queue configuration
            handler: Async message handler function
            auto_ack: Whether to auto-acknowledge messages
            prefetch_count: Number of messages to prefetch

        Raises:
            MessageConsumeError: If consumption fails
        """
        try:
            # Declare queue
            queue = await self.client.declare_queue(queue_config)

            # Set QoS
            channel = self.client.get_channel()
            await channel.set_qos(prefetch_count=prefetch_count)

            # Create message processor
            async def process_message(message: IncomingMessage) -> None:
                try:
                    # Parse message
                    body = json.loads(message.body.decode())

                    logger.debug(
                        "message_received",
                        queue=queue_config.name,
                        correlation_id=message.correlation_id,
                    )

                    # Handle message
                    result = await handler(body)

                    # Send reply if needed
                    if message.reply_to and result is not None:
                        await self._send_reply(message, result)

                    # Acknowledge message
                    if not auto_ack:
                        await message.ack()

                    logger.debug(
                        "message_processed",
                        queue=queue_config.name,
                        correlation_id=message.correlation_id,
                    )

                except json.JSONDecodeError as e:
                    logger.error(
                        "message_decode_failed",
                        queue=queue_config.name,
                        error=str(e),
                    )
                    # Reject and don't requeue malformed messages
                    await message.reject(requeue=False)

                except Exception as e:
                    logger.error(
                        "message_processing_failed",
                        queue=queue_config.name,
                        error=str(e),
                    )
                    # Reject and requeue for retry
                    await message.reject(requeue=True)

            # Start consuming
            consumer_tag = await queue.consume(process_message, no_ack=auto_ack)
            self._consumers[queue_config.name] = consumer_tag

            logger.info(
                "consumer_started",
                queue=queue_config.name,
                prefetch_count=prefetch_count,
            )

        except Exception as e:
            logger.error(
                "consumer_start_failed",
                queue=queue_config.name,
                error=str(e),
            )
            raise MessageConsumeError(
                queue=queue_config.name,
                message=f"Failed to start consumer: {e}",
            ) from e

    async def _send_reply(self, message: IncomingMessage, result: Any) -> None:
        """
        Send reply message for RPC pattern.

        Args:
            message: Original message
            result: Reply payload
        """
        try:
            from aio_pika import DeliveryMode, Message

            reply_body = json.dumps(result).encode()

            reply_message = Message(
                body=reply_body,
                correlation_id=message.correlation_id,
                delivery_mode=DeliveryMode.NOT_PERSISTENT,
                content_type="application/json",
            )

            channel = self.client.get_channel()
            reply_to = message.reply_to
            if reply_to:  # Type guard
                await channel.default_exchange.publish(
                    reply_message,
                    routing_key=reply_to,
                )

            logger.debug(
                "reply_sent",
                correlation_id=message.correlation_id,
                reply_to=message.reply_to,
            )

        except Exception as e:
            logger.error(
                "reply_send_failed",
                correlation_id=message.correlation_id,
                error=str(e),
            )

    async def stop_consuming(self, queue_name: str) -> None:
        """
        Stop consuming from a specific queue.

        Args:
            queue_name: Queue name
        """
        try:
            if queue_name in self._consumers:
                self._consumers.pop(queue_name)
                # Consumer will be cancelled when connection closes
                logger.info("consumer_stopped", queue=queue_name)

        except Exception as e:
            logger.error(
                "consumer_stop_failed",
                queue=queue_name,
                error=str(e),
            )

    async def stop_all(self) -> None:
        """Stop all consumers."""
        try:
            for queue_name in list(self._consumers.keys()):
                await self.stop_consuming(queue_name)

            logger.info("all_consumers_stopped")

        except Exception as e:
            logger.error("consumers_stop_all_failed", error=str(e))

    async def run_consumer(
        self,
        queue_config: QueueConfig,
        handler: MessageHandler,
        auto_ack: bool = False,
        prefetch_count: int = 10,
    ) -> None:
        """
        Run consumer in blocking mode (for worker processes).

        Args:
            queue_config: Queue configuration
            handler: Async message handler function
            auto_ack: Whether to auto-acknowledge messages
            prefetch_count: Number of messages to prefetch
        """
        try:
            self._running = True

            # Start consuming
            await self.consume(
                queue_config=queue_config,
                handler=handler,
                auto_ack=auto_ack,
                prefetch_count=prefetch_count,
            )

            logger.info("consumer_running", queue=queue_config.name)

            # Keep running until stopped
            while self._running:
                await asyncio.sleep(1)

        except KeyboardInterrupt:
            logger.info("consumer_interrupted")
            self._running = False

        except Exception as e:
            logger.error(
                "consumer_run_failed",
                queue=queue_config.name,
                error=str(e),
            )
            raise MessageConsumeError(
                queue=queue_config.name,
                message=f"Consumer run failed: {e}",
            ) from e

        finally:
            await self.stop_all()

    def stop(self) -> None:
        """Stop the consumer gracefully."""
        self._running = False
        logger.info("consumer_stop_requested")
