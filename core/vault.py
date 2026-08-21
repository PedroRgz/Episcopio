"""Server-side, session-scoped credential vault.

Why this exists
---------------
The previous dashboard kept a single module-level ``EpiscopioAPIClient`` and
stashed the user's API keys on it. Because a Dash server serves every visitor
from the same process, that meant one visitor's keys were applied to *every*
other visitor's requests, and one visitor flipping to "real data" flipped it
for everybody. The keys were also round-tripped through a ``dcc.Store``, so
they travelled to the browser in clear text and came back on every callback.

This vault fixes both halves of that bug:

* Credentials are held **only** on the server, in memory, indexed by an opaque
  128-bit session id. The browser holds the id, never the secrets.
* Every read and write is scoped to one session id, so sessions cannot observe
  or influence each other.

Entries expire on a sliding TTL and the whole vault is bounded, so an
unauthenticated visitor cannot grow it without limit. Nothing here is
persisted: a restart drops every credential, which is the desired behaviour for
keys a user pasted into a browser.
"""
from __future__ import annotations

import logging
import secrets as pysecrets
import threading
import time
from dataclasses import dataclass, field
from typing import Dict, List, Optional

from ingesta.providers import get_provider, mask

logger = logging.getLogger(__name__)

SESSION_ID_BYTES = 32
DEFAULT_TTL_SECONDS = 60 * 60
DEFAULT_MAX_SESSIONS = 500


class SessionExpired(KeyError):
    """Raised when a session id is unknown or has timed out."""


@dataclass
class _Session:
    """One browser session's credentials plus its expiry bookkeeping."""
    created_at: float
    last_seen: float
    credentials: Dict[str, Dict[str, str]] = field(default_factory=dict)


class CredentialVault:
    """Thread-safe, TTL-bounded, session-scoped credential store."""

    def __init__(
        self,
        ttl_seconds: int = DEFAULT_TTL_SECONDS,
        max_sessions: int = DEFAULT_MAX_SESSIONS,
    ):
        self.ttl_seconds = ttl_seconds
        self.max_sessions = max_sessions
        self._sessions: Dict[str, _Session] = {}
        self._lock = threading.Lock()

    # -- lifecycle ---------------------------------------------------------

    def create_session(self) -> str:
        """Mint a new session id and return it.

        The id is the only thing that ever reaches the browser, and it is
        generated with :mod:`secrets` so it cannot be guessed.
        """
        session_id = pysecrets.token_urlsafe(SESSION_ID_BYTES)
        now = time.monotonic()
        with self._lock:
            self._evict_locked(now)
            self._sessions[session_id] = _Session(created_at=now, last_seen=now)
        return session_id

    def _evict_locked(self, now: float) -> None:
        """Drop expired sessions, then the oldest ones if still over budget."""
        expired = [
            sid for sid, s in self._sessions.items() if now - s.last_seen > self.ttl_seconds
        ]
        for sid in expired:
            self._sessions.pop(sid, None)

        overflow = len(self._sessions) - self.max_sessions + 1
        if overflow > 0:
            oldest = sorted(self._sessions.items(), key=lambda kv: kv[1].last_seen)
            for sid, _ in oldest[:overflow]:
                self._sessions.pop(sid, None)
            logger.info("Vault sobre capacidad: %d sesiones desalojadas", overflow)

    def _touch_locked(self, session_id: str, now: float) -> _Session:
        session = self._sessions.get(session_id)
        if session is None or now - session.last_seen > self.ttl_seconds:
            self._sessions.pop(session_id, None)
            raise SessionExpired("La sesión expiró o no existe.")
        session.last_seen = now
        return session

    def is_active(self, session_id: Optional[str]) -> bool:
        """True when the id names a live session (never raises)."""
        if not session_id:
            return False
        with self._lock:
            try:
                self._touch_locked(session_id, time.monotonic())
                return True
            except SessionExpired:
                return False

    def ensure_session(self, session_id: Optional[str]) -> str:
        """Return ``session_id`` if it is still live, otherwise mint a new one."""
        if self.is_active(session_id):
            return session_id  # type: ignore[return-value]
        return self.create_session()

    def destroy(self, session_id: Optional[str]) -> None:
        """Forget a session and everything in it."""
        if not session_id:
            return
        with self._lock:
            self._sessions.pop(session_id, None)

    # -- credentials -------------------------------------------------------

    def set_credentials(self, session_id: str, provider_id: str, creds: Dict[str, str]) -> None:
        """Store one provider's credentials for a session.

        Empty values are dropped, and a provider whose fields are all empty is
        removed entirely — that is how the UI "disconnects" a source.

        Raises:
            SessionExpired: if the session is unknown or timed out.
            ValueError: if ``provider_id`` is not in the registry.
        """
        provider = get_provider(provider_id)
        if provider is None:
            raise ValueError(f"Proveedor desconocido: {provider_id!r}")

        allowed = {f.name for f in provider.fields}
        cleaned = {
            k: v.strip()
            for k, v in (creds or {}).items()
            if k in allowed and isinstance(v, str) and v.strip()
        }

        with self._lock:
            session = self._touch_locked(session_id, time.monotonic())
            if cleaned:
                session.credentials[provider_id] = cleaned
            else:
                session.credentials.pop(provider_id, None)

    def get_credentials(self, session_id: str, provider_id: str) -> Dict[str, str]:
        """Return a copy of one provider's credentials for a session."""
        with self._lock:
            session = self._touch_locked(session_id, time.monotonic())
            return dict(session.credentials.get(provider_id, {}))

    def all_credentials(self, session_id: str) -> Dict[str, Dict[str, str]]:
        """Return a deep-ish copy of every credential held for a session."""
        with self._lock:
            session = self._touch_locked(session_id, time.monotonic())
            return {pid: dict(creds) for pid, creds in session.credentials.items()}

    def connected_providers(self, session_id: str) -> List[str]:
        """Ids of providers this session has supplied credentials for."""
        with self._lock:
            session = self._touch_locked(session_id, time.monotonic())
            return sorted(session.credentials.keys())

    def masked_snapshot(self, session_id: str) -> Dict[str, Dict[str, str]]:
        """A redacted view safe to render in the UI or write to a log."""
        with self._lock:
            session = self._touch_locked(session_id, time.monotonic())
            snapshot: Dict[str, Dict[str, str]] = {}
            for pid, creds in session.credentials.items():
                provider = get_provider(pid)
                secret_fields = (
                    {f.name for f in provider.fields if f.secret} if provider else set(creds)
                )
                snapshot[pid] = {
                    k: (mask(v) if k in secret_fields else v) for k, v in creds.items()
                }
            return snapshot

    # -- introspection -----------------------------------------------------

    def session_count(self) -> int:
        with self._lock:
            return len(self._sessions)

    def purge_expired(self) -> int:
        """Drop expired sessions; returns how many were removed."""
        now = time.monotonic()
        with self._lock:
            before = len(self._sessions)
            expired = [
                sid for sid, s in self._sessions.items() if now - s.last_seen > self.ttl_seconds
            ]
            for sid in expired:
                self._sessions.pop(sid, None)
            return before - len(self._sessions)


# Process-wide vault. Sessions inside it are isolated from one another, which
# is the property the old global API client lacked.
vault = CredentialVault()
