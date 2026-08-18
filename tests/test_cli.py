import json

from agent_run_replay import JsonlRunStore, RunMetadata, RunRecorder
from agent_run_replay.cli import main


def record(store, run_id: str, text: str) -> None:
    recorder = RunRecorder(store, RunMetadata(run_id, agent="assistant"))
    recorder.model_request("m1", {"prompt": "hello"})
    recorder.model_response("m1", {"text": text})
    recorder.complete({"text": text})


def test_inspect_outputs_summary(tmp_path, capsys) -> None:
    record(JsonlRunStore(tmp_path), "run-1", "hi")
    assert main(["--store", str(tmp_path), "inspect", "run-1"]) == 0
    output = json.loads(capsys.readouterr().out)
    assert output["run_id"] == "run-1"
    assert output["event_count"] == 4


def test_replay_reports_zero_external_calls(tmp_path, capsys) -> None:
    record(JsonlRunStore(tmp_path), "run-1", "hi")
    assert main(["--store", str(tmp_path), "replay", "run-1"]) == 0
    output = json.loads(capsys.readouterr().out)
    assert output == {
        "external_calls": 0,
        "model_calls": 1,
        "run_id": "run-1",
        "tool_calls": 0,
        "valid": True,
    }


def test_diff_returns_one_for_different_runs(tmp_path, capsys) -> None:
    store = JsonlRunStore(tmp_path)
    record(store, "left", "hi")
    record(store, "right", "different")
    assert main(["--store", str(tmp_path), "diff", "left", "right"]) == 1
    assert json.loads(capsys.readouterr().out)["equal"] is False


def test_missing_run_returns_usage_error(tmp_path, capsys) -> None:
    assert main(["--store", str(tmp_path), "inspect", "missing"]) == 2
    assert "run not found" in capsys.readouterr().err
