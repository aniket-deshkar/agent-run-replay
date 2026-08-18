"""High-level agent execution recorder."""

from __future__ import annotations

from collections.abc import Callable, Mapping
from datetime import UTC, datetime
from typing import Any, Protocol

from .model import EventKind, JsonValue, RunEvent, RunMetadata
from .redaction import NoOpRedactor, Redactor
from .storage import JsonlRunStore


class EventSink(Protocol):
    def append(self, event: RunEvent) -> None: ...


class RunRecorder:
    def __init__(
        self,
        sink: EventSink,
        metadata: RunMetadata,
        *,
        redactor: Redactor | None = None,
        clock: Callable[[], datetime] | None = None,
    ) -> None:
        self._sink = sink
        self.metadata = metadata
        self._redactor = redactor or NoOpRedactor()
        self._clock = clock or (lambda: datetime.now(UTC))
        self._sequence = 0
        self._closed = False
        self._record(
            EventKind.RUN_STARTED,
            {
                "session_id": metadata.session_id,
                "agent": metadata.agent,
                "attributes": dict(metadata.attributes),
            },
        )

    @classmethod
    def to_directory(
        cls,
        directory: str,
        metadata: RunMetadata,
        *,
        redactor: Redactor | None = None,
    ) -> RunRecorder:
        return cls(JsonlRunStore(directory), metadata, redactor=redactor)

    def model_request(self, call_id: str, request: Mapping[str, JsonValue]) -> RunEvent:
        return self._exchange(EventKind.MODEL_REQUEST, call_id, "request", request)

    def model_response(self, call_id: str, response: Mapping[str, JsonValue]) -> RunEvent:
        return self._exchange(EventKind.MODEL_RESPONSE, call_id, "response", response)

    def tool_request(self, call_id: str, tool: str, arguments: Mapping[str, JsonValue]) -> RunEvent:
        return self._record(
            EventKind.TOOL_REQUEST,
            {"call_id": call_id, "tool": tool, "arguments": dict(arguments)},
        )

    def tool_response(self, call_id: str, response: Mapping[str, JsonValue]) -> RunEvent:
        return self._exchange(EventKind.TOOL_RESPONSE, call_id, "response", response)

    def state_snapshot(self, state: Mapping[str, JsonValue]) -> RunEvent:
        return self._record(EventKind.STATE_SNAPSHOT, {"state": dict(state)})

    def state_delta(self, delta: Mapping[str, JsonValue]) -> RunEvent:
        return self._record(EventKind.STATE_DELTA, {"delta": dict(delta)})

    def complete(self, result: Mapping[str, JsonValue] | None = None) -> RunEvent:
        event = self._record(EventKind.RUN_COMPLETED, {"result": dict(result or {})})
        self._closed = True
        return event

    def fail(self, error_type: str, message: str) -> RunEvent:
        event = self._record(
            EventKind.RUN_FAILED,
            {"error_type": error_type, "message": message},
        )
        self._closed = True
        return event

    def _exchange(
        self,
        kind: EventKind,
        call_id: str,
        field: str,
        value: Mapping[str, JsonValue],
    ) -> RunEvent:
        if not call_id.strip():
            raise ValueError("call_id must not be blank")
        return self._record(kind, {"call_id": call_id, field: dict(value)})

    def _record(self, kind: EventKind, payload: Mapping[str, JsonValue]) -> RunEvent:
        if self._closed:
            raise RuntimeError("run is already closed")
        redacted = self._redactor.redact(payload)
        event = RunEvent.create(
            self.metadata.run_id,
            self._sequence,
            kind,
            redacted,
            occurred_at=self._clock(),
        )
        self._sink.append(event)
        self._sequence += 1
        return event

    def __enter__(self) -> RunRecorder:
        return self

    def __exit__(
        self, exception_type: type[BaseException] | None, exception: Any, traceback: Any
    ) -> None:
        if self._closed:
            return
        if exception is None:
            self.complete()
        else:
            self.fail(exception_type.__name__, str(exception))
