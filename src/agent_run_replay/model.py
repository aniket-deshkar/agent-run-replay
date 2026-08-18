"""Typed append-only execution events."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import StrEnum
from types import MappingProxyType
from typing import Any

JsonValue = None | bool | int | float | str | list["JsonValue"] | dict[str, "JsonValue"]


class EventKind(StrEnum):
    RUN_STARTED = "run.started"
    MODEL_REQUEST = "model.request"
    MODEL_RESPONSE = "model.response"
    TOOL_REQUEST = "tool.request"
    TOOL_RESPONSE = "tool.response"
    STATE_SNAPSHOT = "state.snapshot"
    STATE_DELTA = "state.delta"
    RUN_COMPLETED = "run.completed"
    RUN_FAILED = "run.failed"


@dataclass(frozen=True, slots=True)
class RunMetadata:
    run_id: str
    session_id: str | None = None
    agent: str | None = None
    attributes: Mapping[str, JsonValue] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.run_id.strip():
            raise ValueError("run_id must not be blank")
        object.__setattr__(self, "attributes", MappingProxyType(dict(self.attributes)))


@dataclass(frozen=True, slots=True)
class RunEvent:
    run_id: str
    sequence: int
    kind: EventKind
    payload: Mapping[str, JsonValue]
    occurred_at: datetime
    schema_version: int = 1

    def __post_init__(self) -> None:
        if not self.run_id.strip():
            raise ValueError("run_id must not be blank")
        if self.sequence < 0:
            raise ValueError("sequence must be non-negative")
        if self.schema_version != 1:
            raise ValueError("unsupported schema_version")
        if self.occurred_at.tzinfo is None:
            raise ValueError("occurred_at must be timezone-aware")
        object.__setattr__(self, "payload", MappingProxyType(dict(self.payload)))

    @classmethod
    def create(
        cls,
        run_id: str,
        sequence: int,
        kind: EventKind,
        payload: Mapping[str, JsonValue],
        *,
        occurred_at: datetime | None = None,
    ) -> RunEvent:
        return cls(run_id, sequence, kind, payload, occurred_at or datetime.now(UTC))

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "run_id": self.run_id,
            "sequence": self.sequence,
            "kind": self.kind.value,
            "occurred_at": self.occurred_at.isoformat(),
            "payload": dict(self.payload),
        }

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> RunEvent:
        required = {"schema_version", "run_id", "sequence", "kind", "occurred_at", "payload"}
        missing = required.difference(value)
        if missing:
            raise ValueError(f"event is missing fields: {', '.join(sorted(missing))}")
        payload = value["payload"]
        if not isinstance(payload, dict):
            raise ValueError("payload must be an object")
        return cls(
            schema_version=int(value["schema_version"]),
            run_id=str(value["run_id"]),
            sequence=int(value["sequence"]),
            kind=EventKind(value["kind"]),
            occurred_at=datetime.fromisoformat(str(value["occurred_at"])),
            payload=payload,
        )
