"""Structural run comparison."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

from .model import EventKind, JsonValue, RunEvent


class DifferenceKind(StrEnum):
    ADDED = "added"
    REMOVED = "removed"
    KIND_CHANGED = "kind_changed"
    PAYLOAD_CHANGED = "payload_changed"


@dataclass(frozen=True, slots=True)
class Difference:
    index: int
    kind: DifferenceKind
    left_kind: EventKind | None
    right_kind: EventKind | None
    left_payload: dict[str, JsonValue] | None
    right_payload: dict[str, JsonValue] | None


@dataclass(frozen=True, slots=True)
class RunDiff:
    differences: tuple[Difference, ...]

    @property
    def equal(self) -> bool:
        return not self.differences


def diff_runs(left: list[RunEvent], right: list[RunEvent]) -> RunDiff:
    differences: list[Difference] = []
    for index in range(max(len(left), len(right))):
        left_event = left[index] if index < len(left) else None
        right_event = right[index] if index < len(right) else None
        if left_event is None:
            differences.append(_difference(index, DifferenceKind.ADDED, None, right_event))
        elif right_event is None:
            differences.append(_difference(index, DifferenceKind.REMOVED, left_event, None))
        elif left_event.kind != right_event.kind:
            differences.append(
                _difference(index, DifferenceKind.KIND_CHANGED, left_event, right_event)
            )
        elif dict(left_event.payload) != dict(right_event.payload):
            differences.append(
                _difference(index, DifferenceKind.PAYLOAD_CHANGED, left_event, right_event)
            )
    return RunDiff(tuple(differences))


def _difference(
    index: int,
    kind: DifferenceKind,
    left: RunEvent | None,
    right: RunEvent | None,
) -> Difference:
    return Difference(
        index=index,
        kind=kind,
        left_kind=left.kind if left else None,
        right_kind=right.kind if right else None,
        left_payload=dict(left.payload) if left else None,
        right_payload=dict(right.payload) if right else None,
    )
