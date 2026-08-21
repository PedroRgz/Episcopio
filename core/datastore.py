"""Session-scoped store for pipeline results.

Each session gets one dataset: the series, KPIs and alerts produced by its most
recent successful run. Like the vault, this is per-session and in-memory, so a
visitor only ever sees data derived from the credentials they supplied.

When a session has no dataset the dashboard falls back to the bundled sample
data, which is what makes the app explorable before any key is entered.
"""
from __future__ import annotations

import threading
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

DATASET_TTL_SECONDS = 60 * 60
MAX_DATASETS = 500


@dataclass
class Dataset:
    """One session's materialised view of its data."""
    serie_oficial: List[Dict[str, Any]] = field(default_factory=list)
    serie_social: List[Dict[str, Any]] = field(default_factory=list)
    kpis: Dict[str, Any] = field(default_factory=dict)
    alertas: List[Dict[str, Any]] = field(default_factory=list)
    fuentes: List[str] = field(default_factory=list)
    generated_at: str = ""
    _monotonic: float = field(default_factory=time.monotonic, repr=False)

    @property
    def is_empty(self) -> bool:
        return not self.serie_oficial and not self.serie_social

    def to_dict(self) -> Dict[str, Any]:
        return {
            "serie_oficial": self.serie_oficial,
            "serie_social": {"menciones": self.serie_social},
            "kpis": self.kpis,
            "alertas": self.alertas,
            "fuentes": self.fuentes,
            "generated_at": self.generated_at,
            "is_sample": False,
        }


class DataStore:
    """Thread-safe, TTL-bounded map of session id -> :class:`Dataset`."""

    def __init__(self, ttl_seconds: int = DATASET_TTL_SECONDS, max_datasets: int = MAX_DATASETS):
        self.ttl_seconds = ttl_seconds
        self.max_datasets = max_datasets
        self._data: Dict[str, Dataset] = {}
        self._lock = threading.Lock()

    def put(self, session_id: str, dataset: Dataset) -> None:
        dataset.generated_at = dataset.generated_at or datetime.now(timezone.utc).isoformat(
            timespec="seconds"
        )
        with self._lock:
            self._purge_locked()
            if len(self._data) >= self.max_datasets and session_id not in self._data:
                oldest = min(self._data.items(), key=lambda kv: kv[1]._monotonic)[0]
                self._data.pop(oldest, None)
            self._data[session_id] = dataset

    def get(self, session_id: Optional[str]) -> Optional[Dataset]:
        """Return a session's dataset, or ``None`` if absent or expired."""
        if not session_id:
            return None
        with self._lock:
            dataset = self._data.get(session_id)
            if dataset is None:
                return None
            if time.monotonic() - dataset._monotonic > self.ttl_seconds:
                self._data.pop(session_id, None)
                return None
            return dataset

    def clear(self, session_id: Optional[str]) -> None:
        if not session_id:
            return
        with self._lock:
            self._data.pop(session_id, None)

    def _purge_locked(self) -> None:
        cutoff = time.monotonic() - self.ttl_seconds
        for sid in [s for s, d in self._data.items() if d._monotonic < cutoff]:
            self._data.pop(sid, None)


data_store = DataStore()
