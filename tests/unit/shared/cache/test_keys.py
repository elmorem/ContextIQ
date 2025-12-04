"""
Tests for cache keys.
"""

import uuid

from shared.cache.keys import CacheKeys


class TestSessionKeys:
    """Tests for session cache keys."""

    def test_session_key(self):
        """Test generating session cache key."""
        session_id = str(uuid.uuid4())
        key = CacheKeys.session(session_id)
        assert key == f"session:{session_id}"

    def test_session_state_key(self):
        """Test generating session state cache key."""
        session_id = str(uuid.uuid4())
        key = CacheKeys.session_state(session_id)
        assert key == f"session:{session_id}:state"

    def test_session_events_key(self):
        """Test generating session events cache key."""
        session_id = str(uuid.uuid4())
        key = CacheKeys.session_events(session_id)
        assert key == f"session:{session_id}:events"


class TestMemoryKeys:
    """Tests for memory cache keys."""

    def test_memory_key(self):
        """Test generating memory cache key."""
        memory_id = str(uuid.uuid4())
        key = CacheKeys.memory(memory_id)
        assert key == f"memory:{memory_id}"

    def test_memories_by_scope_key(self):
        """Test generating memories by scope cache key."""
        scope_hash = "abc123"
        key = CacheKeys.memories_by_scope(scope_hash)
        assert key == f"memory:scope:{scope_hash}"

    def test_memory_search_results_key(self):
        """Test generating memory search results cache key."""
        query_hash = "xyz789"
        key = CacheKeys.memory_search_results(query_hash)
        assert key == f"memory:search:{query_hash}"


class TestJobKeys:
    """Tests for job cache keys."""

    def test_extraction_job_key(self):
        """Test generating extraction job cache key."""
        job_id = str(uuid.uuid4())
        key = CacheKeys.extraction_job(job_id)
        assert key == f"job:extraction:{job_id}"

    def test_consolidation_job_key(self):
        """Test generating consolidation job cache key."""
        job_id = str(uuid.uuid4())
        key = CacheKeys.consolidation_job(job_id)
        assert key == f"job:consolidation:{job_id}"


class TestUserKeys:
    """Tests for user cache keys."""

    def test_user_preferences_key(self):
        """Test generating user preferences cache key."""
        user_id = "user123"
        key = CacheKeys.user_preferences(user_id)
        assert key == f"user:{user_id}:preferences"

    def test_user_sessions_key(self):
        """Test generating user sessions cache key."""
        user_id = "user123"
        key = CacheKeys.user_sessions(user_id)
        assert key == f"user:{user_id}:sessions"


class TestConfigKeys:
    """Tests for config cache keys."""

    def test_config_key(self):
        """Test generating config cache key."""
        config_name = "llm_settings"
        key = CacheKeys.config(config_name)
        assert key == f"config:{config_name}"

    def test_feature_flags_key(self):
        """Test generating feature flags cache key."""
        key = CacheKeys.feature_flags()
        assert key == "config:feature_flags"


class TestKeyPatterns:
    """Tests for cache key patterns."""

    def test_all_sessions_pattern(self):
        """Test pattern for all sessions."""
        pattern = f"{CacheKeys.SESSION_PREFIX}{CacheKeys.SEPARATOR}*"
        assert pattern == "session:*"

    def test_session_state_pattern(self):
        """Test pattern for all session states."""
        pattern = f"{CacheKeys.SESSION_PREFIX}{CacheKeys.SEPARATOR}*{CacheKeys.SEPARATOR}state"
        assert pattern == "session:*:state"

    def test_all_memories_pattern(self):
        """Test pattern for all memories."""
        pattern = f"{CacheKeys.MEMORY_PREFIX}{CacheKeys.SEPARATOR}*"
        assert pattern == "memory:*"

    def test_all_jobs_pattern(self):
        """Test pattern for all jobs."""
        pattern = f"{CacheKeys.JOB_PREFIX}{CacheKeys.SEPARATOR}*"
        assert pattern == "job:*"


class TestKeySeparator:
    """Tests for key separator."""

    def test_separator_is_colon(self):
        """Test that separator is colon."""
        assert CacheKeys.SEPARATOR == ":"

    def test_all_keys_use_separator(self):
        """Test that all generated keys use the separator."""
        session_id = str(uuid.uuid4())
        memory_id = str(uuid.uuid4())

        keys = [
            CacheKeys.session(session_id),
            CacheKeys.session_state(session_id),
            CacheKeys.memory(memory_id),
            CacheKeys.config("test"),
        ]

        for key in keys:
            assert CacheKeys.SEPARATOR in key
