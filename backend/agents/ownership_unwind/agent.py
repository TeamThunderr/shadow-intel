from agents.base import BaseAgent
from shared.schemas import AgentResponse, EntityFingerprint


class OwnershipUnwindAgent(BaseAgent):
    """
    Recursively unwinds corporate ownership to find Ultimate Beneficial Owner.
    Detects circular ownership (shell company indicator).
    Owner: Person 3
    """

    @property
    def module_name(self) -> str:
        return "ownership_unwind"

    async def run(self, fingerprint: EntityFingerprint) -> AgentResponse:
        # TODO (P3): Implement recursive ownership graph
        # Steps:
        # 1. Query OpenOwnership for entity
        # 2. Query Companies House + SEC EDGAR
        # 3. Build NetworkX directed graph
        # 4. Traverse up to 10 levels deep
        # 5. Detect UBO + circular ownership
        # 6. Serialize graph to JSON for D3.js

        self.logger.info(f"Running for: {fingerprint.canonical_name}")

        return AgentResponse(
            module=self.module_name,
            entity_id=fingerprint.entity_id,
            risk_score=0.0,
            evidence=[],
            data={
                "ownership_graph": {"nodes": [], "edges": []},
                "ultimate_beneficial_owner": None,
                "circular_ownership_detected": False,
                "status": "stub — implement in graph.py and sources/"
            }
        )
