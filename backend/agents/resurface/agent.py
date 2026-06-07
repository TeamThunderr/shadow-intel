from agents.base import BaseAgent
from shared.schemas import AgentResponse, EntityFingerprint


class ResurfaceAlertEngine(BaseAgent):
    """
    Monitors for new registrations matching entity fingerprint.
    Fires Teams/Outlook alert when confidence exceeds threshold.
    Owner: Person 4
    """

    @property
    def module_name(self) -> str:
        return "resurface_engine"

    async def run(self, fingerprint: EntityFingerprint) -> AgentResponse:
        # TODO (P4): Implement watchlist polling + Teams/Outlook alerts
        # Steps:
        # 1. Check OpenCorporates for recent registrations matching fingerprint
        # 2. Check WHOIS for new domain registrations
        # 3. Score matches against fingerprint
        # 4. If score > threshold: trigger alerts/teams.py + alerts/outlook.py

        self.logger.info(f"Running resurface check for: {fingerprint.canonical_name}")

        return AgentResponse(
            module=self.module_name,
            entity_id=fingerprint.entity_id,
            risk_score=0.0,
            evidence=[],
            data={"resurface_events": [], "status": "stub — implement in agent.py + scheduler.py"}
        )
