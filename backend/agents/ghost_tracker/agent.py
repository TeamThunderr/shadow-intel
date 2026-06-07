from agents.base import BaseAgent
from shared.schemas import AgentResponse, EntityFingerprint, EvidenceItem, AgentStatus
from shared.utils import generate_entity_id
from shared.config import get_settings
from .fingerprint import build_fingerprint
from .sources.opensanctions import query_opensanctions
from .sources.ofac import query_ofac
from .sources.opencorporates import query_opencorporates


class GhostEntityTracker(BaseAgent):
    """
    Entry point agent. Detects sanctions matches, builds entity fingerprint,
    and passes it to all subsequent agents.
    """

    @property
    def module_name(self) -> str:
        return "ghost_tracker"

    async def run(self, fingerprint: EntityFingerprint) -> AgentResponse:
        settings = get_settings()
        evidence: list[EvidenceItem] = []
        aliases: list[str] = []
        jurisdictions: list[str] = []
        sanctions_lists: list[str] = []

        # 1. Query OpenSanctions
        os_results = await query_opensanctions(fingerprint.canonical_name, settings)
        if os_results:
            for match in os_results:
                aliases.extend(match.get("aliases", []))
                jurisdictions.extend(match.get("jurisdictions", []))
                sanctions_lists.append(match.get("source", "opensanctions"))
                evidence.append(EvidenceItem(
                    source="OpenSanctions",
                    type="sanctions_match",
                    detail=f"Matched: {match.get('name')} | Score: {match.get('score', 0):.2f}",
                    url=match.get("url"),
                    confidence=match.get("score", 0.0),
                ))

        # 2. Query OFAC SDN list
        ofac_results = await query_ofac(fingerprint.canonical_name)
        if ofac_results:
            for match in ofac_results:
                sanctions_lists.append("OFAC")
                evidence.append(EvidenceItem(
                    source="OFAC SDN",
                    type="sanctions_match",
                    detail=f"OFAC match: {match.get('name')}",
                    confidence=match.get("confidence", 0.8),
                ))

        # 3. Query OpenCorporates for director overlaps
        corp_results = await query_opencorporates(fingerprint.canonical_name, settings)
        if corp_results:
            for corp in corp_results:
                jurisdictions.append(corp.get("jurisdiction", ""))
                evidence.append(EvidenceItem(
                    source="OpenCorporates",
                    type="corporate_match",
                    detail=f"Similar entity: {corp.get('name')} in {corp.get('jurisdiction')}",
                    url=corp.get("url"),
                    confidence=corp.get("similarity", 0.7),
                ))

        # 4. Build updated fingerprint
        fingerprint.aliases = list(set(aliases))
        fingerprint.jurisdictions = list(set(j for j in jurisdictions if j))
        fingerprint.sanctions_lists = list(set(sanctions_lists))

        # 5. Calculate confidence score
        confidence = min(1.0, (
            (0.4 if sanctions_lists else 0.0) +
            (0.3 * min(len(evidence) / 5, 1.0)) +
            (0.3 * min(len(jurisdictions) / 3, 1.0))
        ))

        return AgentResponse(
            module=self.module_name,
            entity_id=fingerprint.entity_id,
            risk_score=confidence,
            evidence=evidence,
            data={
                "fingerprint": fingerprint.model_dump(),
                "sanctions_lists": fingerprint.sanctions_lists,
                "alias_count": len(fingerprint.aliases),
                "jurisdiction_count": len(fingerprint.jurisdictions),
            }
        )
