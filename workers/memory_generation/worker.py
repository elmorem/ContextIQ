"""
Memory generation worker.

Background worker that consumes memory generation requests from RabbitMQ
and processes them through the extraction/embedding pipeline.
"""

import asyncio
import logging
from typing import Any

from shared.clients import MemoryServiceClient, SessionsServiceClient
from shared.clients.config import HTTPClientSettings
from shared.embedding import EmbeddingService, EmbeddingSettings
from shared.extraction import ExtractionEngine, ExtractionSettings
from shared.messaging import MessageConsumer, RabbitMQClient
from shared.messaging.config import MessagingSettings
from shared.messaging.queues import Queues
from shared.vector_store import QdrantClientWrapper, QdrantSettings
from workers.memory_generation.config import WorkerSettings, get_worker_settings
from workers.memory_generation.models import MemoryGenerationRequest
from workers.memory_generation.processor import MemoryGenerationProcessor

logger = logging.getLogger(__name__)


class MemoryGenerationWorker:
    """
    Worker for processing memory generation requests.

    Consumes messages from RabbitMQ and orchestrates the memory extraction,
    embedding generation, and storage pipeline.
    """

    def __init__(
        self,
        worker_settings: WorkerSettings | None = None,
        extraction_settings: ExtractionSettings | None = None,
        embedding_settings: EmbeddingSettings | None = None,
        qdrant_settings: QdrantSettings | None = None,
        messaging_settings: MessagingSettings | None = None,
        http_client_settings: HTTPClientSettings | None = None,
    ):
        """
        Initialize memory generation worker.

        Args:
            worker_settings: Worker configuration
            extraction_settings: Extraction engine settings
            embedding_settings: Embedding service settings
            qdrant_settings: Qdrant client settings
            messaging_settings: RabbitMQ messaging settings
            http_client_settings: HTTP client configuration
        """
        self.worker_settings = worker_settings or get_worker_settings()
        self.http_client_settings = http_client_settings or HTTPClientSettings()

        # Initialize services
        self.extraction_engine = ExtractionEngine(settings=extraction_settings)
        self.embedding_service = EmbeddingService(settings=embedding_settings)
        self.vector_store = QdrantClientWrapper(settings=qdrant_settings)

        # Initialize HTTP service clients
        self.sessions_client = SessionsServiceClient(
            base_url=self.http_client_settings.sessions_service_url,
            timeout=self.http_client_settings.sessions_service_timeout,
            max_retries=self.http_client_settings.sessions_service_max_retries,
            retry_delay=self.http_client_settings.sessions_service_retry_delay,
        )
        self.memory_client = MemoryServiceClient(
            base_url=self.http_client_settings.memory_service_url,
            timeout=self.http_client_settings.memory_service_timeout,
            max_retries=self.http_client_settings.memory_service_max_retries,
            retry_delay=self.http_client_settings.memory_service_retry_delay,
        )

        # Initialize processor with HTTP clients
        self.processor = MemoryGenerationProcessor(
            extraction_engine=self.extraction_engine,
            embedding_service=self.embedding_service,
            vector_store=self.vector_store,
            sessions_client=self.sessions_client,
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

            # Start consuming messages from extraction requests queue
            await self.consumer.run_consumer(
                queue_config=Queues.EXTRACTION_REQUESTS,
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

        # Close HTTP clients
        await self.sessions_client.close()
        await self.memory_client.close()

        self.extraction_engine.close()
        self.embedding_service.close()
        self.vector_store.close()

        logger.info(f"{self.worker_settings.worker_name} stopped")

    async def handle_message(
        self,
        message_data: dict[str, Any],
    ) -> dict[str, Any] | None:
        """
        Handle incoming memory generation request message.

        Args:
            message_data: Parsed message data

        Returns:
            Result dict if successful, None otherwise
        """
        try:
            # Parse request
            request = MemoryGenerationRequest(**message_data)

            logger.info(f"Received memory generation request for session {request.session_id}")

            # Validate request
            is_valid, error = self.processor.validate_request(request)
            if not is_valid:
                logger.error(f"Invalid request for session {request.session_id}: {error}")
                raise ValueError(f"Invalid request: {error}")

            # Process the request (processor now fetches events from Sessions Service)
            result = await self.processor.process_request(request)

            if result.success:
                logger.info(
                    f"Successfully processed session {request.session_id}: "
                    f"{result.memories_extracted} memories extracted, "
                    f"{result.embeddings_generated} embeddings generated"
                )
                # Return result for potential reply queue
                return {
                    "session_id": str(result.session_id),
                    "user_id": str(result.user_id),
                    "memories_extracted": result.memories_extracted,
                    "memories_saved": result.memories_saved,
                    "embeddings_generated": result.embeddings_generated,
                    "success": True,
                }
            else:
                logger.error(f"Failed to process session {request.session_id}: {result.error}")
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

    worker = MemoryGenerationWorker()

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
