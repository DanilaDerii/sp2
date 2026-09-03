"""Validation helpers for SP2 MCP tool arguments."""

from __future__ import annotations

from typing import Any


def without_none_values(data: dict[str, Any]) -> dict[str, Any]:
    """Return a copy of data without keys whose values are None."""
    return {key: value for key, value in data.items() if value is not None}


def positive_int(value: int, field_name: str) -> int:
    """Validate and normalize a positive integer tool argument."""
    if isinstance(value, bool):
        raise ValueError(f"{field_name} must be a positive integer")
    try:
        resolved_value = int(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{field_name} must be a positive integer") from exc
    if resolved_value <= 0:
        raise ValueError(f"{field_name} must be a positive integer")
    return resolved_value


def required_text(
    value: str,
    field_name: str,
    *,
    normalize_whitespace: bool = False,
) -> str:
    """Validate and normalize a required text tool argument."""
    if not isinstance(value, str):
        raise ValueError(f"{field_name} must be text")
    normalized_value = value.strip()
    if normalize_whitespace:
        normalized_value = " ".join(value.split()).strip()
    if not normalized_value:
        raise ValueError(f"{field_name} must not be empty")
    return normalized_value
