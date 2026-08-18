from datetime import UTC, datetime

import pytest

from agent_run_replay import EventKind, JsonlRunStore, RunEvent


def event(run_id: str, sequence: int) -> RunEvent:
    return RunEvent.create(
        run_id,
        sequence,
        EventKind.RUN_STARTED,
        {},
        occurred_at=datetime(2026, 1, 2, tzinfo=UTC),
    )


def test_append_and_load_jsonl(tmp_path) -> None:
    store = JsonlRunStore(tmp_path)
    store.append(event("run-1", 0))
    assert store.load("run-1") == [event("run-1", 0)]
    assert store.list_run_ids() == ["run-1"]


def test_append_requires_contiguous_sequence(tmp_path) -> None:
    store = JsonlRunStore(tmp_path)
    with pytest.raises(ValueError, match="expected sequence 0"):
        store.append(event("run-1", 1))


def test_run_id_cannot_escape_storage_root(tmp_path) -> None:
    store = JsonlRunStore(tmp_path)
    with pytest.raises(ValueError, match="unsafe"):
        store.load("../secrets")


def test_corrupt_line_has_location(tmp_path) -> None:
    store = JsonlRunStore(tmp_path)
    store.path_for("run-1").write_text("not-json\n", encoding="utf-8")
    with pytest.raises(ValueError, match="line 1"):
        store.load("run-1")


def test_missing_run_is_explicit(tmp_path) -> None:
    with pytest.raises(FileNotFoundError, match="run not found"):
        JsonlRunStore(tmp_path).load("missing")
