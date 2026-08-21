"""Shared types for ingestion connectors."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List


@dataclass
class ConnectorResult:
    """What a connector reports back to the pipeline.

    ``ok`` means "this source contributed usable data". A connector that could
    not run because it was not configured reports ``ok=False`` with
    ``status="skipped"`` — it never reports a fake success, which is what the
    previous mock connectors did.
    """
    source: str
    ok: bool
    status: str  # "ok" | "skipped" | "error" | "unreachable"
    message: str
    records: int = 0
    data: List[Dict[str, Any]] = field(default_factory=list)

    @classmethod
    def skipped(cls, source: str, message: str) -> "ConnectorResult":
        return cls(source=source, ok=False, status="skipped", message=message)

    @classmethod
    def error(cls, source: str, message: str) -> "ConnectorResult":
        return cls(source=source, ok=False, status="error", message=message)

    @classmethod
    def unreachable(cls, source: str, message: str) -> "ConnectorResult":
        return cls(source=source, ok=False, status="unreachable", message=message)

    @classmethod
    def success(
        cls, source: str, records: int, message: str, data: List[Dict[str, Any]] | None = None
    ) -> "ConnectorResult":
        return cls(
            source=source,
            ok=True,
            status="ok",
            message=message,
            records=records,
            data=data or [],
        )
