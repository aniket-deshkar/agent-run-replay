"""Command-line inspection, replay validation, and diffing."""

from __future__ import annotations

import argparse
import json
import sys
from collections.abc import Sequence
from pathlib import Path
from typing import Any

from .diff import diff_runs
from .inspect import summarize
from .replay import ReplayTape
from .storage import JsonlRunStore


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="agent-run-replay")
    parser.add_argument("--store", type=Path, default=Path(".agent-runs"))
    subparsers = parser.add_subparsers(dest="command", required=True)

    subparsers.add_parser("list", help="List recorded run IDs")

    inspect_parser = subparsers.add_parser("inspect", help="Inspect a recorded run")
    inspect_parser.add_argument("run_id")
    inspect_parser.add_argument("--events", action="store_true")

    replay_parser = subparsers.add_parser("replay", help="Validate the local replay tape")
    replay_parser.add_argument("run_id")

    diff_parser = subparsers.add_parser("diff", help="Compare two recorded runs")
    diff_parser.add_argument("left_run_id")
    diff_parser.add_argument("right_run_id")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    arguments = build_parser().parse_args(argv)
    store = JsonlRunStore(arguments.store)
    try:
        if arguments.command == "list":
            for run_id in store.list_run_ids():
                print(run_id)
            return 0
        if arguments.command == "inspect":
            events = store.load(arguments.run_id)
            summary = summarize(events)
            output: dict[str, Any] = {
                "run_id": summary.run_id,
                "event_count": summary.event_count,
                "terminal_kind": summary.terminal_kind.value if summary.terminal_kind else None,
                "counts": {kind.value: count for kind, count in summary.counts.items()},
            }
            if arguments.events:
                output["events"] = [event.to_dict() for event in events]
            print(json.dumps(output, indent=2, sort_keys=True))
            return 0
        if arguments.command == "replay":
            tape = ReplayTape(store.load(arguments.run_id))
            print(
                json.dumps(
                    {
                        "run_id": tape.run_id,
                        "model_calls": tape.model_call_count,
                        "tool_calls": tape.tool_call_count,
                        "external_calls": 0,
                        "valid": True,
                    },
                    indent=2,
                    sort_keys=True,
                )
            )
            return 0
        left = store.load(arguments.left_run_id)
        right = store.load(arguments.right_run_id)
        result = diff_runs(left, right)
        print(
            json.dumps(
                {
                    "equal": result.equal,
                    "differences": [
                        {
                            "index": item.index,
                            "kind": item.kind.value,
                            "left_kind": item.left_kind.value if item.left_kind else None,
                            "right_kind": item.right_kind.value if item.right_kind else None,
                            "left_payload": item.left_payload,
                            "right_payload": item.right_payload,
                        }
                        for item in result.differences
                    ],
                },
                indent=2,
                sort_keys=True,
            )
        )
        return 0 if result.equal else 1
    except (FileNotFoundError, ValueError) as error:
        print(str(error), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
