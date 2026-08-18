# Contributing

Create a focused branch and run:

```bash
ruff check .
ruff format --check .
pytest
python -m build
```

Keep the runtime dependency-light and event schemas backward-aware. Add failure tests for corrupt storage, mismatched replay inputs, and redaction changes. Never commit recorded runs, credentials, virtual environments, caches, or build artifacts.
