"""
Consolidation worker.

Background worker that consumes consolidation requests from RabbitMQ
and processes memory deduplication and merging.
"""

import asyncio
import logging
from typing import Any

from shared.clients import MemoryServiceClient
from shared.clients.config import HTTPClientSettings
from shared.consolidation import ConsolidationEngine, ConsolidationSettings
from shared.embedding import EmbeddingService, EmbeddingSettings
from shared.messaging import MessageConsumer, RabbitMQClient
from shared.messaging.config import MessagingSettings
from shared.messaging.queues import Queues
from workers.consolidation.config import (
    ConsolidationWorkerSettings,
    get_consolidation_worker_settings,
)
from workers.consolidation.models import ConsolidationRequest
from workers.consolidation.processor import ConsolidationProcessor

logger = logging.getLogger(__name__)


class ConsolidationWorker:
    """
    Worker for processing consolidation requests.

    Consumes messages from RabbitMQ and orchestrates memory consolidation pipeline.
    """

    def __init__(
        self,
        worker_settings: ConsolidationWorkerSettings | None = None,
        consolidation_settings: ConsolidationSettings | None = None,
        embedding_settings: EmbeddingSettings | None = None,
        messaging_settings: MessagingSettings | None = None,
        http_client_settings: HTTPClientSettings | None = None,
    ):
        """
        Initialize consolidation worker.

        Args:
            worker_settings: Worker configuration
            consolidation_settings: Consolidation engine settings
            embedding_settings: Embedding service settings
            messaging_settings: RabbitMQ messaging settings
            http_client_settings: HTTP client configuration
        """
        self.worker_settings = worker_settings or get_consolidation_worker_settings()
        self.http_client_settings = http_client_settings or HTTPClientSettings()

        # Initialize services
        self.consolidation_engine = ConsolidationEngine(settings=consolidation_settings)
        self.embedding_service = EmbeddingService(settings=embedding_settings)

        # Initialize HTTP service client
        self.memory_client = MemoryServiceClient(
            base_url=self.http_client_settings.memory_service_url,
            timeout=self.http_client_settings.memory_service_timeout,
            max_retries=self.http_client_settings.memory_service_max_retries,
            retry_delay=self.http_client_settings.memory_service_retry_delay,
        )

        # Initialize processor with HTTP client
        self.processor = ConsolidationProcessor(
            consolidation_engine=self.consolidation_engine,
            embedding_service=self.embedding_service,
            memory_client=self.memory_client,
        )

        # Initialize RabbitMQ client and consumer
        self.messaging_settings = messaging_settings or MessagingSettings()
        self.rabbitmq_client = RabbitMQClient(url=self.messaging_settings.rabbitmq_url)
        self.consumer = MessageConsumer(client=self.rabbitmq_client)

        self._is_running = False

    async def start(self) -> None:
        """Start the worker and begin consuming messages."""
        logger.info(
            f"Starting {self.worker_settings.worker_name} "
            f"(concurrency: {self.worker_settings.worker_concurrency})"
        )

        self._is_running = True

        try:
            # Connect to RabbitMQ
            await self.rabbitmq_client.connect()

            # Start consuming messages from consolidation requests queue
            await self.consumer.run_consumer(
                queue_config=Queues.CONSOLIDATION_REQUESTS,
                handler=self.handle_message,
                auto_ack=False,
                prefetch_count=self.worker_settings.worker_prefetch_count,
            )

            logger.info(f"{self.worker_settings.worker_name} started successfully")

        except Exception as e:
            logger.exception(f"Error starting worker: {e}")
            self._is_running = False
            raise

    async def stop(self) -> None:
        """Stop the worker and cleanup resources."""
        logger.info(f"Stopping {self.worker_settings.worker_name}")

        self._is_running = False

        # Stop consumer and close RabbitMQ connection
        self.consumer.stop()
        await self.consumer.stop_all()
        await self.rabbitmq_client.disconnect()

        # Close HTTP client
        await self.memory_client.close()

        self.consolidation_engine.close()
        self.embedding_service.close()

        logger.info(f"{self.worker_settings.worker_name} stopped")

    async def handle_message(
        self,
        message_data: dict[str, Any],
    ) -> dict[str, Any] | None:
        """
        Handle incoming consolidation request message.

        Args:
            message_data: Parsed message data

        Returns:
            Result dict if successful, None otherwise
        """
        try:
            # Parse request
            request = ConsolidationRequest(**message_data)

            logger.info(f"Received consolidation request for scope {request.scope}")

            # Validate request
            is_valid, error = self.processor.validate_request(request)
            if not is_valid:
                logger.error(f"Invalid request for scope {request.scope}: {error}")
                raise ValueError(f"Invalid request: {error}")

            # Process the request
            result = await self.processor.process_request(request)

            if result.success:
                logger.info(
                    f"Successfully processed scope {request.scope}: "
                    f"{result.memories_merged} merged, "
                    f"{result.conflicts_detected} conflicts"
                )
                # Return result for potential reply queue
                return {
                    "scope": result.scope,
                    "memories_processed": result.memories_processed,
                    "memories_merged": result.memories_merged,
                    "conflicts_detected": result.conflicts_detected,
                    "memories_updated": result.memories_updated,
                    "success": True,
                }
            else:
                logger.error(f"Failed to process scope {request.scope}: {result.error}")
                raise RuntimeError(f"Processing failed: {result.error}")

        except Exception as e:
            logger.exception(f"Error handling message: {e}")
            # Re-raise to trigger message requeue
            raise

    @property
    def is_running(self) -> bool:
        """Check if worker is currently running."""
        return self._is_running


async def main() -> None:
    """Main entry point for the worker."""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )

    worker = ConsolidationWorker()

    try:
        await worker.start()

        # Keep worker running
        while worker.is_running:
            await asyncio.sleep(1)

    except KeyboardInterrupt:
        logger.info("Received shutdown signal")
    finally:
        await worker.stop()


if __name__ == "__main__":
    asyncio.run(main())
