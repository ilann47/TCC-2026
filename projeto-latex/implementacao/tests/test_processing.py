from datetime import datetime, timezone
from uuid import UUID

from app.shared.processing import canonical_event, content_hash
from app.shared.schemas import AuditEvent


def sample_event() -> AuditEvent:
    return AuditEvent(
        event_id=UUID("12345678-1234-5678-1234-567812345678"),
        event_type="user.updated",
        entity_type="user",
        entity_id="42",
        actor_id="admin-1",
        source="test-suite",
        occurred_at=datetime(2026, 8, 11, 12, 0, tzinfo=timezone.utc),
        payload={"field": "email"},
    )


def test_canonical_representation_is_stable() -> None:
    event = sample_event()
    assert canonical_event(event) == canonical_event(event.model_copy())


def test_content_hash_is_sha256() -> None:
    digest = content_hash(sample_event())
    assert len(digest) == 64
    assert digest == content_hash(sample_event())


def test_nested_payload_key_order_does_not_change_digest() -> None:
    first = sample_event().model_copy(update={"payload": {"b": 2, "a": {"z": 3, "x": 4}}})
    second = sample_event().model_copy(update={"payload": {"a": {"x": 4, "z": 3}, "b": 2}})
    assert canonical_event(first) == canonical_event(second)
    assert content_hash(first) == content_hash(second)


def test_changed_content_changes_digest() -> None:
    event = sample_event()
    changed = event.model_copy(update={"payload": {"field": "phone"}})
    assert content_hash(event) != content_hash(changed)
