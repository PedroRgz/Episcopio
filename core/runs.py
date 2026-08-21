"""In-memory registry of pipeline runs.

The dashboard needs to show "what happened when I pasted my keys" without
blocking a callback for the length of a full ingest. The pipeline therefore
runs on a background thread and reports progress into this registry, which the
UI polls.

Like the credential vault, everything here is per-session and in-process: one
session can only ever see its own runs, and nothing survives a restart.
"""
from __future__ import annotations

import threading
import time
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from typing import Dict, List, Optional

# Run states
PENDING = "pending"
RUNNING = "running"
SUCCESS = "success"
PARTIAL = "partial"
ERROR = "error"

TERMINAL_STATES = {SUCCESS, PARTIAL, ERROR}

MAX_RUNS_PER_SESSION = 10
RUN_TTL_SECONDS = 60 * 60


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


@dataclass
class RunStep:
    """One unit of work inside a run (usually one provider)."""
    key: str
    label: str
    status: str = PENDING
    message: str = ""
    records: int = 0
    started_at: Optional[str] = None
    finished_at: Optional[str] = None

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class PipelineRun:
    """A single end-to-end execution triggered by a session's credentials."""
    id: str
    session_id: str
    status: str = PENDING
    created_at: str = field(default_factory=_now_iso)
    finished_at: Optional[str] = None
    steps: List[RunStep] = field(default_factory=list)
    summary: str = ""
    _monotonic: float = field(default_factory=time.monotonic, repr=False)

    def step(self, key: str) -> Optional[RunStep]:
        for s in self.steps:
            if s.key == key:
                return s
        return None

    @property
    def is_finished(self) -> bool:
        return self.status in TERMINAL_STATES

    @property
    def total_records(self) -> int:
        return sum(s.records for s in self.steps)

    def to_dict(self) -> dict:
        """Serialise for the API/UI. Contains no credentials by construction."""
        return {
            "id": self.id,
            "status": self.status,
            "created_at": self.created_at,
            "finished_at": self.finished_at,
            "summary": self.summary,
            "total_records": self.total_records,
            "steps": [s.to_dict() for s in self.steps],
        }


class RunRegistry:
    """Thread-safe store of runs, bounded per session."""

    def __init__(
        self,
        max_runs_per_session: int = MAX_RUNS_PER_SESSION,
        ttl_seconds: int = RUN_TTL_SECONDS,
    ):
        self.max_runs_per_session = max_runs_per_session
        self.ttl_seconds = ttl_seconds
        self._runs: Dict[str, List[PipelineRun]] = {}
        self._lock = threading.Lock()
        self._counter = 0

    def create(self, session_id: str, steps: List[RunStep]) -> PipelineRun:
        """Register a new run in the ``pending`` state."""
        with self._lock:
            self._counter += 1
            run = PipelineRun(
                id=f"run-{self._counter}-{int(time.time())}",
                session_id=session_id,
                steps=list(steps),
            )
            runs = self._runs.setdefault(session_id, [])
            runs.append(run)
            # Keep only the most recent runs for this session.
            if len(runs) > self.max_runs_per_session:
                del runs[: len(runs) - self.max_runs_per_session]
            self._purge_locked()
            return run

    def _purge_locked(self) -> None:
        cutoff = time.monotonic() - self.ttl_seconds
        for sid in list(self._runs):
            kept = [r for r in self._runs[sid] if r._monotonic >= cutoff]
            if kept:
                self._runs[sid] = kept
            else:
                del self._runs[sid]

    def latest(self, session_id: str) -> Optional[PipelineRun]:
        """Most recent run for a session, or ``None``."""
        with self._lock:
            runs = self._runs.get(session_id)
            return runs[-1] if runs else None

    def get(self, session_id: str, run_id: str) -> Optional[PipelineRun]:
        """Fetch one run, scoped to its owning session.

        Scoping by ``session_id`` here is what stops a guessed run id from
        exposing another session's results.
        """
        with self._lock:
            for run in self._runs.get(session_id, []):
                if run.id == run_id:
                    return run
        return None

    def history(self, session_id: str) -> List[PipelineRun]:
        with self._lock:
            return list(self._runs.get(session_id, []))

    def clear(self, session_id: str) -> None:
        with self._lock:
            self._runs.pop(session_id, None)

    # -- mutation helpers used by the pipeline ----------------------------

    def mark_running(self, run: PipelineRun) -> None:
        with self._lock:
            run.status = RUNNING

    def update_step(
        self,
        run: PipelineRun,
        key: str,
        *,
        status: str,
        message: str = "",
        records: int = 0,
    ) -> None:
        """Record the outcome of one step."""
        with self._lock:
            step = run.step(key)
            if step is None:
                return
            if status == RUNNING and step.started_at is None:
                step.started_at = _now_iso()
            step.status = status
            step.message = message
            step.records = records
            if status in TERMINAL_STATES:
                step.finished_at = _now_iso()

    def finish(self, run: PipelineRun, status: str, summary: str) -> None:
        with self._lock:
            run.status = status
            run.summary = summary
            run.finished_at = _now_iso()


run_registry = RunRegistry()
