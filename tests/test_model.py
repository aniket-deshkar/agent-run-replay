from datetime import UTC, datetime

import pytest

from agent_run_replay import EventKind, RunEvent, RunMetadata


def test_event_round_trip() -> None:
    event = RunEvent.create(
        "run-1",
        0,
        EventKind.STATE_SNAPSHOT,
        {"state": {"step": 1}},
        occurred_at=datetime(2026, 1, 2, tzinfo=UTC),
    )
    assert RunEvent.from_dict(event.to_dict()) == event


def test_event_rejects_naive_timestamp() -> None:
    with pytest.raises(ValueError, match="timezone-aware"):
        RunEvent("run-1", 0, EventKind.RUN_STARTED, {}, datetime(2026, 1, 2))


def test_event_rejects_unknown_schema() -> None:
    with pytest.raises(ValueError, match="unsupported"):
        RunEvent(
            "run-1",
            0,
            EventKind.RUN_STARTED,
            {},
            datetime(2026, 1, 2, tzinfo=UTC),
            schema_version=2,
        )


def test_metadata_copies_attributes() -> None:
    attributes = {"tenant": "north"}
    metadata = RunMetadata("run-1", attributes=attributes)
    attributes["tenant"] = "south"
    assert metadata.attributes["tenant"] == "north"


def test_from_dict_requires_payload_object() -> None:
    with pytest.raises(ValueError, match="payload"):
        RunEvent.from_dict(
            {
                "schema_version": 1,
                "run_id": "run-1",
                "sequence": 0,
                "kind": "run.started",
                "occurred_at": "2026-01-02T00:00:00+00:00",
                "payload": [],
            }
        )
