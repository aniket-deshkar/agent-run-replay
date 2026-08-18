from datetime import UTC, datetime

import pytest

from agent_run_replay import EventKind, KeyRedactor, RunMetadata, RunRecorder


class MemorySink:
    def __init__(self) -> None:
        self.events = []

    def append(self, event) -> None:
        self.events.append(event)


def fixed_clock() -> datetime:
    return datetime(2026, 1, 2, 3, 4, tzinfo=UTC)


def test_records_full_run_with_contiguous_sequences() -> None:
    sink = MemorySink()
    recorder = RunRecorder(sink, RunMetadata("run-1", session_id="session-1"), clock=fixed_clock)
    recorder.model_request("m1", {"messages": ["hello"]})
    recorder.model_response("m1", {"text": "hi"})
    recorder.tool_request("t1", "weather", {"city": "Pune"})
    recorder.tool_response("t1", {"temperature": 28})
    recorder.state_snapshot({"answer": "hi"})
    recorder.complete({"text": "done"})

    assert [item.sequence for item in sink.events] == list(range(7))
    assert sink.events[0].kind == EventKind.RUN_STARTED
    assert sink.events[-1].kind == EventKind.RUN_COMPLETED


def test_recursively_redacts_sensitive_keys() -> None:
    sink = MemorySink()
    recorder = RunRecorder(
        sink,
        RunMetadata("run-1"),
        redactor=KeyRedactor({"api_key", "authorization"}),
        clock=fixed_clock,
    )
    recorder.tool_request(
        "t1",
        "call-api",
        {"api_key": "secret", "headers": {"Authorization": "Bearer secret"}},
    )

    arguments = sink.events[1].payload["arguments"]
    assert arguments == {
        "api_key": "[REDACTED]",
        "headers": {"Authorization": "[REDACTED]"},
    }


def test_closed_run_rejects_more_events() -> None:
    recorder = RunRecorder(MemorySink(), RunMetadata("run-1"), clock=fixed_clock)
    recorder.complete()
    with pytest.raises(RuntimeError, match="closed"):
        recorder.state_delta({"step": 2})


def test_context_manager_records_failure_and_propagates() -> None:
    sink = MemorySink()
    with (
        pytest.raises(RuntimeError, match="boom"),
        RunRecorder(sink, RunMetadata("run-1"), clock=fixed_clock),
    ):
        raise RuntimeError("boom")
    assert sink.events[-1].kind == EventKind.RUN_FAILED
    assert sink.events[-1].payload["error_type"] == "RuntimeError"


def test_blank_call_id_is_rejected() -> None:
    recorder = RunRecorder(MemorySink(), RunMetadata("run-1"), clock=fixed_clock)
    with pytest.raises(ValueError, match="call_id"):
        recorder.model_request(" ", {})
