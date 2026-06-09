"""
In-memory investigation session store.
Stores session state and completed reports for the duration of the server process.

Note: Resets on server restart — acceptable for hackathon demo.
For production: replace backing dict with Redis using the same interface.
"""

import asyncio
from typing import Optional
from datetime import datetime

from shared.schemas import (
    InvestigationReport, InvestigationStatus,
    AgentStatuses, EntityFingerprint,
)
from shared.logger import get_logger

logger = get_logger(__name__)


class InvestigationSession:
    """Represents a single investigation — in progress or completed."""

    def __init__(
        self,
        entity_id: str,
        entity_name: str,
        fingerprint: EntityFingerprint,
    ):
        self.entity_id = entity_id
        self.entity_name = entity_name
        self.fingerprint = fingerprint
        self.started_at: datetime = datetime.utcnow()
        self.status: InvestigationStatus = InvestigationStatus(entity_id=entity_id)
        self.report: Optional[InvestigationReport] = None
        self.error: Optional[str] = None

    def to_status(self) -> InvestigationStatus:
        """Return a fresh status snapshot with elapsed time updated."""
        elapsed = int((datetime.utcnow() - self.started_at).total_seconds() * 1000)
        self.status.elapsed_ms = elapsed
        return self.status


class SessionStore:
    """
    Thread-safe in-memory store for investigation sessions.

    Capacity is capped at MAX_SESSIONS. When the cap is hit the oldest
    session (insertion order) is evicted before a new one is added —
    keeping memory bounded during long demo runs.
    """

    MAX_SESSIONS = 100

    def __init__(self) -> None:
        # Dict preserves insertion order in Python 3.7+, giving FIFO eviction
        self._sessions: dict[str, InvestigationSession] = {}
        self._lock = asyncio.Lock()

    async def create(
        self,
        entity_id: str,
        entity_name: str,
        fingerprint: EntityFingerprint,
    ) -> InvestigationSession:
        """Create and register a new session. Evicts the oldest if at capacity."""
        async with self._lock:
            if len(self._sessions) >= self.MAX_SESSIONS:
                oldest_key = next(iter(self._sessions))
                del self._sessions[oldest_key]
                logger.info(f"SessionStore: evicted oldest session ({oldest_key}) to make room")

            session = InvestigationSession(entity_id, entity_name, fingerprint)
            self._sessions[entity_id] = session
            logger.info(f"SessionStore: created session {entity_id} for '{entity_name}'")
            return session

    async def get(self, entity_id: str) -> Optional[InvestigationSession]:
        """Return the session for the given entity_id, or None."""
        return self._sessions.get(entity_id)

    async def complete(self, entity_id: str, report: InvestigationReport) -> None:
        """Mark a session as complete and attach its final report."""
        async with self._lock:
            session = self._sessions.get(entity_id)
            if session:
                session.report = report
                session.status.overall_status = "complete"
                logger.info(f"SessionStore: session {entity_id} marked complete")

    async def fail(self, entity_id: str, error: str) -> None:
        """Mark a session as failed with an error message."""
        async with self._lock:
            session = self._sessions.get(entity_id)
            if session:
                session.error = error
                session.status.overall_status = "failed"
                logger.warning(f"SessionStore: session {entity_id} marked failed — {error}")

    def count(self) -> int:
        """Current number of sessions in the store."""
        return len(self._sessions)


# ─── Global singleton ─────────────────────────────────────────────────────────
# Import this from any module: `from shared.session import store`
store = SessionStore()
