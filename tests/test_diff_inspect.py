from datetime import UTC, datetime, timedelta

import pytest

from agent_run_replay import DifferenceKind, EventKind, RunEvent, diff_runs, summarize

NOW = datetime(2026, 1, 2, tzinfo=UTC)


def event(run_id: str, sequence: int, kind: EventKind, payload: dict, offset: int = 0) -> RunEvent:
    return RunEvent.create(
        run_id,
        sequence,
        kind,
        payload,
        occurred_at=NOW + timedelta(seconds=offset),
    )


def test_diff_ignores_run_identity_and_timestamps() -> None:
    left = [event("left", 0, EventKind.RUN_STARTED, {"agent": "a"})]
    right = [event("right", 0, EventKind.RUN_STARTED, {"agent": "a"}, 20)]
    assert diff_runs(left, right).equal


def test_diff_reports_payload_and_added_events() -> None:
    left = [event("left", 0, EventKind.STATE_SNAPSHOT, {"state": {"step": 1}})]
    right = [
        event("right", 0, EventKind.STATE_SNAPSHOT, {"state": {"step": 2}}),
        event("right", 1, EventKind.RUN_COMPLETED, {"result": {}}),
    ]
    result = diff_runs(left, right)
    assert [item.kind for item in result.differences] == [
        DifferenceKind.PAYLOAD_CHANGED,
        DifferenceKind.ADDED,
    ]


def test_summary_counts_and_terminal_state() -> None:
    events = [
        event("run-1", 0, EventKind.RUN_STARTED, {}),
        event("run-1", 1, EventKind.STATE_DELTA, {"delta": {}}),
        event("run-1", 2, EventKind.RUN_COMPLETED, {"result": {}}),
    ]
    summary = summarize(events)
    assert summary.event_count == 3
    assert summary.terminal_kind == EventKind.RUN_COMPLETED
    assert summary.counts[EventKind.STATE_DELTA] == 1


def test_summary_rejects_mixed_runs() -> None:
    with pytest.raises(ValueError, match="multiple"):
        summarize(
            [
                event("one", 0, EventKind.RUN_STARTED, {}),
                event("two", 1, EventKind.RUN_COMPLETED, {}),
            ]
        )
