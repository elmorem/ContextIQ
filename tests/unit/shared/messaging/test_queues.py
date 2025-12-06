"""
Unit tests for queue configurations.
"""

from shared.messaging.queues import QueueConfig, Queues


class TestQueueConfig:
    """Tests for QueueConfig dataclass."""

    def test_queue_config_defaults(self):
        """Test default values for queue configuration."""
        config = QueueConfig(name="test.queue")

        assert config.name == "test.queue"
        assert config.durable is True
        assert config.auto_delete is False
        assert config.exchange is None
        assert config.routing_key is None

    def test_queue_config_with_exchange(self):
        """Test queue configuration with exchange binding."""
        config = QueueConfig(
            name="test.queue",
            exchange="test.exchange",
            routing_key="test.key",
            durable=False,
            auto_delete=True,
        )

        assert config.name == "test.queue"
        assert config.exchange == "test.exchange"
        assert config.routing_key == "test.key"
        assert config.durable is False
        assert config.auto_delete is True


class TestQueues:
    """Tests for Queues class."""

    def test_extraction_requests_queue(self):
        """Test extraction requests queue configuration."""
        queue = Queues.EXTRACTION_REQUESTS

        assert queue.name == "extraction.requests"
        assert queue.exchange == "contextiq.extraction"
        assert queue.routing_key == "extraction.request"
        assert queue.durable is True

    def test_extraction_results_queue(self):
        """Test extraction results queue configuration."""
        queue = Queues.EXTRACTION_RESULTS

        assert queue.name == "extraction.results"
        assert queue.exchange == "contextiq.extraction"
        assert queue.routing_key == "extraction.result"

    def test_consolidation_requests_queue(self):
        """Test consolidation requests queue configuration."""
        queue = Queues.CONSOLIDATION_REQUESTS

        assert queue.name == "consolidation.requests"
        assert queue.exchange == "contextiq.consolidation"
        assert queue.routing_key == "consolidation.request"

    def test_consolidation_results_queue(self):
        """Test consolidation results queue configuration."""
        queue = Queues.CONSOLIDATION_RESULTS

        assert queue.name == "consolidation.results"
        assert queue.exchange == "contextiq.consolidation"
        assert queue.routing_key == "consolidation.result"

    def test_session_events_queue(self):
        """Test session events queue configuration."""
        queue = Queues.SESSION_EVENTS

        assert queue.name == "session.events"
        assert queue.exchange == "contextiq.events"
        assert queue.routing_key == "session.*"

    def test_memory_events_queue(self):
        """Test memory events queue configuration."""
        queue = Queues.MEMORY_EVENTS

        assert queue.name == "memory.events"
        assert queue.exchange == "contextiq.events"
        assert queue.routing_key == "memory.*"

    def test_dead_letter_queue(self):
        """Test dead letter queue configuration."""
        queue = Queues.DEAD_LETTER

        assert queue.name == "dead_letter"
        assert queue.exchange == "contextiq.dlx"
        assert queue.routing_key == "dead_letter"

    def test_all_queues(self):
        """Test that all_queues returns all defined queues."""
        all_queues = Queues.all_queues()

        assert len(all_queues) == 7
        assert Queues.EXTRACTION_REQUESTS in all_queues
        assert Queues.EXTRACTION_RESULTS in all_queues
        assert Queues.CONSOLIDATION_REQUESTS in all_queues
        assert Queues.CONSOLIDATION_RESULTS in all_queues
        assert Queues.SESSION_EVENTS in all_queues
        assert Queues.MEMORY_EVENTS in all_queues
        assert Queues.DEAD_LETTER in all_queues
