"""Append-only JSONL run storage."""

from __future__ import annotations

import json
import os
import re
import threading
from collections.abc import Iterable
from pathlib import Path

from .model import RunEvent

_SAFE_RUN_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,127}$")


class JsonlRunStore:
    def __init__(self, directory: str | Path, *, fsync: bool = False) -> None:
        self.directory = Path(directory)
        self.directory.mkdir(parents=True, exist_ok=True)
        if not self.directory.is_dir():
            raise ValueError("storage path must be a directory")
        self._fsync = fsync
        self._lock = threading.Lock()

    def append(self, event: RunEvent) -> None:
        path = self.path_for(event.run_id)
        with self._lock:
            expected = self._next_sequence(path)
            if event.sequence != expected:
                raise ValueError(f"expected sequence {expected}, received {event.sequence}")
            with path.open("a", encoding="utf-8", newline="\n") as stream:
                stream.write(json.dumps(event.to_dict(), sort_keys=True, separators=(",", ":")))
                stream.write("\n")
                stream.flush()
                if self._fsync:
                    os.fsync(stream.fileno())

    def load(self, run_id: str) -> list[RunEvent]:
        path = self.path_for(run_id)
        if not path.exists():
            raise FileNotFoundError(f"run not found: {run_id}")
        events: list[RunEvent] = []
        with path.open(encoding="utf-8") as stream:
            for line_number, line in enumerate(stream, start=1):
                try:
                    event = RunEvent.from_dict(json.loads(line))
                except (json.JSONDecodeError, TypeError, ValueError) as error:
                    raise ValueError(f"invalid event at line {line_number}: {error}") from error
                if event.run_id != run_id:
                    raise ValueError(f"run id mismatch at line {line_number}")
                if event.sequence != len(events):
                    raise ValueError(f"non-contiguous sequence at line {line_number}")
                events.append(event)
        return events

    def list_run_ids(self) -> list[str]:
        return sorted(path.stem for path in self.directory.glob("*.jsonl") if path.is_file())

    def path_for(self, run_id: str) -> Path:
        if not _SAFE_RUN_ID.fullmatch(run_id):
            raise ValueError("run_id contains unsafe characters")
        return self.directory / f"{run_id}.jsonl"

    def import_events(self, events: Iterable[RunEvent]) -> None:
        for event in events:
            self.append(event)

    @staticmethod
    def _next_sequence(path: Path) -> int:
        if not path.exists():
            return 0
        with path.open(encoding="utf-8") as stream:
            return sum(1 for line in stream if line.strip())
