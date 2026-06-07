from agents.base import BaseAgent
from shared.schemas import AgentResponse, EntityFingerprint


class MoneyTrailAgent(BaseAgent):
    """
    Traces financial flows: crypto wallets, offshore banking, laundering patterns.
    Owner: Person 2
    """

    @property
    def module_name(self) -> str:
        return "money_trail"

    async def run(self, fingerprint: EntityFingerprint) -> AgentResponse:
        # TODO (P2): Implement blockchain tracing, FinCEN lookup, FATF scoring
        # Steps:
        # 1. Query blockchain explorers for wallet addresses linked to entity
        # 2. Trace hops up to 5 levels
        # 3. Detect laundering patterns (placement/layering/integration)
        # 4. Cross-reference FinCEN public data
        # 5. Score with FATF jurisdiction risk

        self.logger.info(f"Running for: {fingerprint.canonical_name}")

        return AgentResponse(
            module=self.module_name,
            entity_id=fingerprint.entity_id,
            risk_score=0.0,
            evidence=[],
            data={"status": "stub — implement in sources/blockchain.py and sources/fincen.py"}
        )
