"""Payload redaction hooks."""

from __future__ import annotations

from collections.abc import Callable, Mapping
from typing import Protocol

from .model import JsonValue


class Redactor(Protocol):
    def redact(self, payload: Mapping[str, JsonValue]) -> dict[str, JsonValue]: ...


class KeyRedactor:
    """Recursively replaces values whose key matches a configured name."""

    def __init__(
        self,
        keys: set[str] | frozenset[str],
        *,
        replacement: str = "[REDACTED]",
        normalize: Callable[[str], str] = str.casefold,
    ) -> None:
        if not keys:
            raise ValueError("at least one redaction key is required")
        self._normalize = normalize
        self._keys = frozenset(normalize(key) for key in keys)
        self._replacement = replacement

    def redact(self, payload: Mapping[str, JsonValue]) -> dict[str, JsonValue]:
        return self._walk(dict(payload))  # type: ignore[return-value]

    def _walk(self, value: JsonValue) -> JsonValue:
        if isinstance(value, dict):
            return {
                key: self._replacement if self._normalize(key) in self._keys else self._walk(item)
                for key, item in value.items()
            }
        if isinstance(value, list):
            return [self._walk(item) for item in value]
        return value


class NoOpRedactor:
    def redact(self, payload: Mapping[str, JsonValue]) -> dict[str, JsonValue]:
        return dict(payload)
