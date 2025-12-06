"""
Memory generation worker.

Background worker that consumes memory generation requests from RabbitMQ
and processes them through the extraction/embedding pipeline.

NOTE: This worker currently uses a placeholder RabbitMQ integration.
TODO: Integrate with shared.messaging.MessageConsumer and shared.messaging.RabbitMQClient
for proper queue management and message consumption.
"""

import asyncio
import json
import logging
from typing import Any

from shared.embedding import EmbeddingService, EmbeddingSettings
from shared.extraction import ExtractionEngine, ExtractionSettings
from shared.messaging import MessageConsumer
from shared.messaging.config import MessagingSettings  # type: ignore[import-untyped]
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
    ):
        """
        Initialize memory generation worker.

        Args:
            worker_settings: Worker configuration
            extraction_settings: Extraction engine settings
            embedding_settings: Embedding service settings
            qdrant_settings: Qdrant client settings
            messaging_settings: RabbitMQ messaging settings
        """
        self.worker_settings = worker_settings or get_worker_settings()

        # Initialize services
        self.extraction_engine = ExtractionEngine(settings=extraction_settings)
        self.embedding_service = EmbeddingService(settings=embedding_settings)
        self.vector_store = QdrantClientWrapper(settings=qdrant_settings)

        # Initialize processor
        self.processor = MemoryGenerationProcessor(
            extraction_engine=self.extraction_engine,
            embedding_service=self.embedding_service,
            vector_store=self.vector_store,
        )

        # Initialize message consumer
        # TODO: Update to use shared.messaging.MessageConsumer properly
        self.consumer = MessageConsumer(settings=messaging_settings)  # type: ignore[call-arg]

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
            await self.consumer.connect()  # type: ignore[attr-defined]

            # Declare queue and start consuming
            await self.consumer.declare_queue(  # type: ignore[attr-defined]
                queue_name=self.worker_settings.memory_generation_queue,
                durable=True,
            )

            await self.consumer.consume(  # type: ignore[call-arg]
                queue_name=self.worker_settings.memory_generation_queue,
                callback=self.handle_message,
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

        # Close connections
        if self.consumer:
            await self.consumer.close()  # type: ignore[attr-defined]

        self.extraction_engine.close()
        self.embedding_service.close()
        self.vector_store.close()

        logger.info(f"{self.worker_settings.worker_name} stopped")

    async def handle_message(
        self,
        body: bytes,
        delivery_tag: int,
        properties: Any,
    ) -> bool:
        """
        Handle incoming memory generation request message.

        Args:
            body: Message body bytes
            delivery_tag: Message delivery tag for acknowledgment
            properties: Message properties

        Returns:
            True if message processed successfully, False otherwise
        """
        try:
            # Parse message
            message_data = json.loads(body.decode("utf-8"))
            request = MemoryGenerationRequest(**message_data)

            logger.info(
                f"Received memory generation request for session {request.session_id}"
            )

            # Validate request
            is_valid, error = self.processor.validate_request(request)
            if not is_valid:
                logger.error(
                    f"Invalid request for session {request.session_id}: {error}"
                )
                return False

            # TODO: Fetch conversation events from Sessions Service
            # For now, using empty list as placeholder
            conversation_events: list[dict[str, str]] = []

            # Process the request
            result = await self.processor.process_request(request, conversation_events)

            if result.success:
                logger.info(
                    f"Successfully processed session {request.session_id}: "
                    f"{result.memories_extracted} memories extracted, "
                    f"{result.embeddings_generated} embeddings generated"
                )
                return True
            else:
                logger.error(
                    f"Failed to process session {request.session_id}: {result.error}"
                )
                return False

        except json.JSONDecodeError as e:
            logger.error(f"Failed to decode message: {e}")
            return False
        except Exception as e:
            logger.exception(f"Error handling message: {e}")
            return False

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
