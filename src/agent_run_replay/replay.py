"""Deterministic response replay with no external client dependency."""

from __future__ import annotations

from collections.abc import Mapping
from copy import deepcopy
from dataclasses import dataclass
from typing import Protocol, TypeVar

from .model import EventKind, JsonValue, RunEvent


class ReplayMismatchError(LookupError):
    pass


@dataclass(frozen=True, slots=True)
class _Exchange:
    request: Mapping[str, JsonValue]
    response: Mapping[str, JsonValue]
    tool: str | None = None


class ReplayTape:
    def __init__(self, events: list[RunEvent]) -> None:
        if not events:
            raise ValueError("a replay tape requires at least one event")
        self.run_id = events[0].run_id
        self._models = self._build(events, EventKind.MODEL_REQUEST, EventKind.MODEL_RESPONSE)
        self._tools = self._build(events, EventKind.TOOL_REQUEST, EventKind.TOOL_RESPONSE)
        self._consumed: set[tuple[str, str]] = set()

    def model_response(
        self, call_id: str, request: Mapping[str, JsonValue]
    ) -> dict[str, JsonValue]:
        exchange = self._lookup("model", self._models, call_id)
        if dict(exchange.request) != dict(request):
            raise ReplayMismatchError(f"model request mismatch for call_id: {call_id}")
        self._consumed.add(("model", call_id))
        return deepcopy(dict(exchange.response))

    def tool_response(
        self,
        call_id: str,
        tool: str,
        arguments: Mapping[str, JsonValue],
    ) -> dict[str, JsonValue]:
        exchange = self._lookup("tool", self._tools, call_id)
        if exchange.tool != tool:
            raise ReplayMismatchError(f"tool name mismatch for call_id: {call_id}")
        if dict(exchange.request) != dict(arguments):
            raise ReplayMismatchError(f"tool argument mismatch for call_id: {call_id}")
        self._consumed.add(("tool", call_id))
        return deepcopy(dict(exchange.response))

    def assert_consumed(self) -> None:
        expected = {("model", call_id) for call_id in self._models} | {
            ("tool", call_id) for call_id in self._tools
        }
        missing = expected.difference(self._consumed)
        if missing:
            names = ", ".join(f"{kind}:{call_id}" for kind, call_id in sorted(missing))
            raise ReplayMismatchError(f"recorded exchanges were not consumed: {names}")

    @property
    def model_call_count(self) -> int:
        return len(self._models)

    @property
    def tool_call_count(self) -> int:
        return len(self._tools)

    @staticmethod
    def _lookup(category: str, exchanges: dict[str, _Exchange], call_id: str) -> _Exchange:
        try:
            return exchanges[call_id]
        except KeyError as error:
            raise ReplayMismatchError(f"unrecorded {category} call_id: {call_id}") from error

    @staticmethod
    def _build(
        events: list[RunEvent], request_kind: EventKind, response_kind: EventKind
    ) -> dict[str, _Exchange]:
        requests: dict[str, tuple[Mapping[str, JsonValue], str | None]] = {}
        responses: dict[str, Mapping[str, JsonValue]] = {}
        request_field = "request" if request_kind == EventKind.MODEL_REQUEST else "arguments"
        for event in events:
            if event.kind not in {request_kind, response_kind}:
                continue
            call_id = event.payload.get("call_id")
            if not isinstance(call_id, str) or not call_id:
                raise ValueError(f"{event.kind.value} is missing call_id")
            if event.kind == request_kind:
                if call_id in requests:
                    raise ValueError(f"duplicate request call_id: {call_id}")
                value = event.payload.get(request_field)
                tool = event.payload.get("tool")
                if not isinstance(value, dict):
                    raise ValueError(f"{event.kind.value} payload must contain {request_field}")
                if tool is not None and not isinstance(tool, str):
                    raise ValueError("tool name must be text")
                requests[call_id] = (value, tool)
            else:
                if call_id in responses:
                    raise ValueError(f"duplicate response call_id: {call_id}")
                value = event.payload.get("response")
                if not isinstance(value, dict):
                    raise ValueError(f"{event.kind.value} payload must contain response")
                responses[call_id] = value
        if requests.keys() != responses.keys():
            missing_responses = requests.keys() - responses.keys()
            orphan_responses = responses.keys() - requests.keys()
            details = sorted(missing_responses | orphan_responses)
            raise ValueError(f"unpaired recorded exchanges: {', '.join(details)}")
        return {
            call_id: _Exchange(request, responses[call_id], tool)
            for call_id, (request, tool) in requests.items()
        }


ResultT = TypeVar("ResultT")


class ReplayAdapter(Protocol[ResultT]):
    """Framework integration point supplied with recorded responses only."""

    def replay(self, tape: ReplayTape) -> ResultT: ...


def replay_with(events: list[RunEvent], adapter: ReplayAdapter[ResultT]) -> ResultT:
    tape = ReplayTape(events)
    result = adapter.replay(tape)
    tape.assert_consumed()
    return result
