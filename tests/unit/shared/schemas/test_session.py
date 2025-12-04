"""
Tests for session schemas.
"""

import uuid
from datetime import datetime

import pytest
from pydantic import ValidationError

from shared.schemas.session import (
    EventCreate,
    EventSchema,
    SessionCreate,
    SessionSchema,
    SessionUpdate,
)


class TestSessionCreate:
    """Tests for SessionCreate schema."""

    def test_valid_session_create(self):
        """Test creating valid session."""
        scope = {"user_id": "123", "org_id": "456"}
        session = SessionCreate(scope=scope, title="Test Session")

        assert session.scope == scope
        assert session.title == "Test Session"
        assert session.state == {}
        assert session.ttl is None

    def test_session_create_with_state(self):
        """Test creating session with initial state."""
        scope = {"user_id": "123"}
        state = {"key": "value"}
        session = SessionCreate(scope=scope, state=state)

        assert session.state == state

    def test_session_create_with_ttl(self):
        """Test creating session with TTL."""
        scope = {"user_id": "123"}
        session = SessionCreate(scope=scope, ttl=3600)

        assert session.ttl == 3600

    def test_scope_required(self):
        """Test that scope is required."""
        with pytest.raises(ValidationError):
            SessionCreate()

    def test_scope_max_keys(self):
        """Test scope max keys validation."""
        scope = {f"key{i}": f"value{i}" for i in range(10)}
        with pytest.raises(ValidationError):
            SessionCreate(scope=scope)

    def test_title_max_length(self):
        """Test title max length validation."""
        scope = {"user_id": "123"}
        long_title = "a" * 600
        with pytest.raises(ValidationError):
            SessionCreate(scope=scope, title=long_title)

    def test_negative_ttl_invalid(self):
        """Test that negative TTL is invalid."""
        scope = {"user_id": "123"}
        with pytest.raises(ValidationError):
            SessionCreate(scope=scope, ttl=-100)


class TestSessionUpdate:
    """Tests for SessionUpdate schema."""

    def test_update_title(self):
        """Test updating session title."""
        update = SessionUpdate(title="New Title")
        assert update.title == "New Title"
        assert update.state is None
        assert update.ttl is None

    def test_update_state(self):
        """Test updating session state."""
        state = {"new": "state"}
        update = SessionUpdate(state=state)
        assert update.state == state

    def test_update_ttl(self):
        """Test updating session TTL."""
        update = SessionUpdate(ttl=7200)
        assert update.ttl == 7200

    def test_update_all_fields(self):
        """Test updating all fields."""
        update = SessionUpdate(title="New", state={"key": "value"}, ttl=3600)
        assert update.title == "New"
        assert update.state == {"key": "value"}
        assert update.ttl == 3600

    def test_empty_update(self):
        """Test empty update is valid."""
        update = SessionUpdate()
        assert update.title is None
        assert update.state is None
        assert update.ttl is None


class TestSessionSchema:
    """Tests for SessionSchema."""

    def test_valid_session_schema(self):
        """Test valid session response schema."""
        session_id = uuid.uuid4()
        scope = {"user_id": "123"}
        now = datetime.utcnow()

        session = SessionSchema(
            id=session_id,
            scope=scope,
            title="Test",
            state={"key": "value"},
            is_active=True,
            last_activity_at=now,
            created_at=now,
            updated_at=now,
        )

        assert session.id == session_id
        assert session.scope == scope
        assert session.title == "Test"
        assert session.is_active is True

    def test_session_schema_from_orm(self):
        """Test creating session schema from ORM object."""

        class MockSession:
            id = uuid.uuid4()
            scope = {"user_id": "123"}
            title = "Test"
            state = {}
            is_active = True
            ttl = None
            last_activity_at = datetime.utcnow()
            created_at = datetime.utcnow()
            updated_at = datetime.utcnow()

        session = SessionSchema.model_validate(MockSession())
        assert str(session.id) == str(MockSession.id)
        assert session.scope == MockSession.scope

    def test_required_fields(self):
        """Test that required fields are enforced."""
        with pytest.raises(ValidationError):
            SessionSchema()

    def test_optional_fields(self):
        """Test optional fields."""
        session_id = uuid.uuid4()
        now = datetime.utcnow()

        session = SessionSchema(
            id=session_id,
            scope={"user_id": "123"},
            title=None,
            state={},
            is_active=True,
            ttl=None,
            last_activity_at=now,
            created_at=now,
            updated_at=now,
        )

        assert session.title is None
        assert session.ttl is None


class TestEventCreate:
    """Tests for EventCreate schema."""

    def test_valid_event_create(self):
        """Test creating valid event."""
        session_id = uuid.uuid4()
        event = EventCreate(
            session_id=session_id,
            event_type="user_action",
            payload={"action": "click", "target": "button"},
        )

        assert event.session_id == session_id
        assert event.event_type == "user_action"
        assert event.payload == {"action": "click", "target": "button"}

    def test_event_type_required(self):
        """Test that event_type is required."""
        session_id = uuid.uuid4()
        with pytest.raises(ValidationError):
            EventCreate(session_id=session_id, payload={})

    def test_event_type_max_length(self):
        """Test event_type max length."""
        session_id = uuid.uuid4()
        with pytest.raises(ValidationError):
            EventCreate(session_id=session_id, event_type="a" * 200, payload={})

    def test_empty_payload(self):
        """Test event with empty payload."""
        session_id = uuid.uuid4()
        event = EventCreate(session_id=session_id, event_type="test", payload={})
        assert event.payload == {}


class TestEventSchema:
    """Tests for EventSchema."""

    def test_valid_event_schema(self):
        """Test valid event response schema."""
        event_id = uuid.uuid4()
        session_id = uuid.uuid4()
        now = datetime.utcnow()

        event = EventSchema(
            id=event_id,
            session_id=session_id,
            event_type="user_action",
            payload={"key": "value"},
            created_at=now,
        )

        assert event.id == event_id
        assert event.session_id == session_id
        assert event.event_type == "user_action"
        assert event.payload == {"key": "value"}
        assert event.created_at == now

    def test_event_schema_from_orm(self):
        """Test creating event schema from ORM object."""

        class MockEvent:
            id = uuid.uuid4()
            session_id = uuid.uuid4()
            event_type = "test"
            payload = {"key": "value"}
            created_at = datetime.utcnow()

        event = EventSchema.model_validate(MockEvent())
        assert str(event.id) == str(MockEvent.id)
        assert event.event_type == MockEvent.event_type

    def test_required_fields(self):
        """Test that required fields are enforced."""
        with pytest.raises(ValidationError):
            EventSchema()
