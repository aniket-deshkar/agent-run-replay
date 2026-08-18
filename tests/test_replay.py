from datetime import UTC, datetime

import pytest

from agent_run_replay import (
    EventKind,
    ReplayMismatchError,
    ReplayTape,
    RunEvent,
    replay_with,
)

NOW = datetime(2026, 1, 2, tzinfo=UTC)


def events() -> list[RunEvent]:
    values = [
        (EventKind.RUN_STARTED, {}),
        (EventKind.MODEL_REQUEST, {"call_id": "m1", "request": {"prompt": "hello"}}),
        (EventKind.MODEL_RESPONSE, {"call_id": "m1", "response": {"text": "hi"}}),
        (
            EventKind.TOOL_REQUEST,
            {"call_id": "t1", "tool": "weather", "arguments": {"city": "Pune"}},
        ),
        (EventKind.TOOL_RESPONSE, {"call_id": "t1", "response": {"temperature": 28}}),
        (EventKind.RUN_COMPLETED, {"result": {"text": "28 C"}}),
    ]
    return [
        RunEvent.create("run-1", index, kind, payload, occurred_at=NOW)
        for index, (kind, payload) in enumerate(values)
    ]


def test_replays_recorded_responses_without_external_provider() -> None:
    tape = ReplayTape(events())
    assert tape.model_response("m1", {"prompt": "hello"}) == {"text": "hi"}
    assert tape.tool_response("t1", "weather", {"city": "Pune"}) == {"temperature": 28}
    tape.assert_consumed()


def test_model_request_mismatch_fails_deterministically() -> None:
    tape = ReplayTape(events())
    with pytest.raises(ReplayMismatchError, match="request mismatch"):
        tape.model_response("m1", {"prompt": "different"})


def test_tool_name_mismatch_fails_deterministically() -> None:
    tape = ReplayTape(events())
    with pytest.raises(ReplayMismatchError, match="tool name"):
        tape.tool_response("t1", "search", {"city": "Pune"})


def test_unconsumed_exchange_is_reported() -> None:
    with pytest.raises(ReplayMismatchError, match="not consumed"):
        ReplayTape(events()).assert_consumed()


def test_unpaired_exchange_is_invalid() -> None:
    with pytest.raises(ValueError, match="unpaired"):
        ReplayTape(events()[:-2])


def test_framework_adapter_receives_only_replay_tape() -> None:
    class Adapter:
        def replay(self, tape: ReplayTape) -> str:
            model = tape.model_response("m1", {"prompt": "hello"})
            tool = tape.tool_response("t1", "weather", {"city": "Pune"})
            return f"{model['text']}:{tool['temperature']}"

    assert replay_with(events(), Adapter()) == "hi:28"
