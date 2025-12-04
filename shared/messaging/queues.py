"""
Queue and exchange definitions.
"""

from dataclasses import dataclass


@dataclass
class QueueConfig:
    """Queue configuration."""

    name: str
    durable: bool = True
    auto_delete: bool = False
    exchange: str | None = None
    routing_key: str | None = None


class Queues:
    """Queue name constants and configurations."""

    # Extraction queues
    EXTRACTION_REQUESTS = QueueConfig(
        name="extraction.requests",
        exchange="contextiq.extraction",
        routing_key="extraction.request",
    )

    EXTRACTION_RESULTS = QueueConfig(
        name="extraction.results",
        exchange="contextiq.extraction",
        routing_key="extraction.result",
    )

    # Consolidation queues
    CONSOLIDATION_REQUESTS = QueueConfig(
        name="consolidation.requests",
        exchange="contextiq.consolidation",
        routing_key="consolidation.request",
    )

    CONSOLIDATION_RESULTS = QueueConfig(
        name="consolidation.results",
        exchange="contextiq.consolidation",
        routing_key="consolidation.result",
    )

    # Event queues
    SESSION_EVENTS = QueueConfig(
        name="session.events",
        exchange="contextiq.events",
        routing_key="session.*",
    )

    MEMORY_EVENTS = QueueConfig(
        name="memory.events",
        exchange="contextiq.events",
        routing_key="memory.*",
    )

    # Dead letter queue
    DEAD_LETTER = QueueConfig(
        name="dead_letter",
        exchange="contextiq.dlx",
        routing_key="dead_letter",
    )

    @classmethod
    def all_queues(cls) -> list[QueueConfig]:
        """
        Get all queue configurations.

        Returns:
            List of queue configurations
        """
        return [
            cls.EXTRACTION_REQUESTS,
            cls.EXTRACTION_RESULTS,
            cls.CONSOLIDATION_REQUESTS,
            cls.CONSOLIDATION_RESULTS,
            cls.SESSION_EVENTS,
            cls.MEMORY_EVENTS,
            cls.DEAD_LETTER,
        ]
