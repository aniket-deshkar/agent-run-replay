"""Run summaries for API and CLI consumers."""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass

from .model import EventKind, RunEvent


@dataclass(frozen=True, slots=True)
class RunSummary:
    run_id: str
    event_count: int
    terminal_kind: EventKind | None
    counts: dict[EventKind, int]


def summarize(events: list[RunEvent]) -> RunSummary:
    if not events:
        raise ValueError("cannot summarize an empty run")
    run_ids = {event.run_id for event in events}
    if len(run_ids) != 1:
        raise ValueError("events contain multiple run ids")
    terminal = (
        events[-1].kind
        if events[-1].kind
        in {
            EventKind.RUN_COMPLETED,
            EventKind.RUN_FAILED,
        }
        else None
    )
    return RunSummary(
        run_id=events[0].run_id,
        event_count=len(events),
        terminal_kind=terminal,
        counts=dict(Counter(event.kind for event in events)),
    )
