from abc import ABC, abstractmethod
from shared.schemas import AgentResponse, EntityFingerprint, AgentStatus
from shared.logger import get_logger
import time


class BaseAgent(ABC):
    """
    All Shadow Intel agents inherit from this class.
    Implement `run()` with your agent logic.
    The base class handles timing, error catching, and status wrapping.
    """

    def __init__(self):
        self.logger = get_logger(self.__class__.__name__)

    @property
    @abstractmethod
    def module_name(self) -> str:
        """Return the module identifier string e.g. 'ghost_tracker'"""
        ...

    @abstractmethod
    async def run(self, fingerprint: EntityFingerprint) -> AgentResponse:
        """
        Execute this agent's investigation logic.
        Receives the entity fingerprint from Ghost Tracker.
        Returns a populated AgentResponse.
        """
        ...

    async def execute(self, fingerprint: EntityFingerprint) -> AgentResponse:
        """Called by the orchestrator. Wraps run() with timing + error handling."""
        start = time.monotonic()
        try:
            self.logger.info(f"Starting for entity_id={fingerprint.entity_id}")
            result = await self.run(fingerprint)
            result.processing_time_ms = int((time.monotonic() - start) * 1000)
            result.status = AgentStatus.complete
            self.logger.info(
                f"Done in {result.processing_time_ms}ms | "
                f"risk={result.risk_score:.2f} | evidence={len(result.evidence)}"
            )
            return result
        except Exception as e:
            elapsed = int((time.monotonic() - start) * 1000)
            self.logger.error(f"Failed after {elapsed}ms: {e}")
            return AgentResponse(
                module=self.module_name,
                entity_id=fingerprint.entity_id,
                status=AgentStatus.failed,
                processing_time_ms=elapsed,
                error=str(e),
            )
