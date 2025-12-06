"""
Unit tests for cache keys.
"""

from shared.cache.keys import CacheKeys


class TestCacheKeys:
    """Tests for cache key generation."""

    def test_session_key(self):
        """Test session cache key."""
        key = CacheKeys.session("session_123")
        assert key == "session:session_123"

    def test_session_events_key(self):
        """Test session events cache key."""
        key = CacheKeys.session_events("session_123")
        assert key == "session:session_123:events"

    def test_session_state_key(self):
        """Test session state cache key."""
        key = CacheKeys.session_state("session_123")
        assert key == "session:session_123:state"

    def test_memory_key(self):
        """Test memory cache key."""
        key = CacheKeys.memory("memory_456")
        assert key == "memory:memory_456"

    def test_memories_by_scope_key(self):
        """Test memories by scope cache key."""
        key = CacheKeys.memories_by_scope("scope_hash_789")
        assert key == "memory:scope:scope_hash_789"

    def test_procedural_memory_key(self):
        """Test procedural memory cache key."""
        key = CacheKeys.procedural_memory("proc_mem_111")
        assert key == "procedural:proc_mem_111"

    def test_procedural_memories_by_type_key(self):
        """Test procedural memories by type cache key."""
        key = CacheKeys.procedural_memories_by_type("scope_hash_222", "workflow")
        assert key == "procedural:scope:scope_hash_222:workflow"

    def test_user_sessions_key(self):
        """Test user sessions cache key."""
        key = CacheKeys.user_sessions("user_333")
        assert key == "user:user_333:sessions"

    def test_agent_sessions_key(self):
        """Test agent sessions cache key."""
        key = CacheKeys.agent_sessions("agent_444")
        assert key == "agent:agent_444:sessions"

    def test_extraction_job_key(self):
        """Test extraction job cache key."""
        key = CacheKeys.extraction_job("job_555")
        assert key == "job:extraction:job_555"

    def test_consolidation_job_key(self):
        """Test consolidation job cache key."""
        key = CacheKeys.consolidation_job("job_666")
        assert key == "job:consolidation:job_666"

    def test_custom_key(self):
        """Test custom cache key."""
        key = CacheKeys.custom("prefix", "middle", "suffix", 123)
        assert key == "prefix:middle:suffix:123"

    def test_custom_key_single_part(self):
        """Test custom cache key with single part."""
        key = CacheKeys.custom("single")
        assert key == "single"
