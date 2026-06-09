"""
Ghost Entity Tracker — Main Agent
Runs all sanctions sources, enriches the entity fingerprint,
and returns a scored AgentResponse.
"""

import asyncio
from agents.base import BaseAgent
from shared.schemas import AgentResponse, EntityFingerprint, EvidenceItem
from shared.config import get_settings
from .fingerprint import enrich_fingerprint
from .sources.ofac import query_ofac
from .sources.un_sanctions import query_un_sanctions
from .sources.opensanctions import query_opensanctions
from .sources.opencorporates import query_opencorporates


class GhostEntityTracker(BaseAgent):
    """
    Entry point agent. Queries all public sanctions lists,
    detects aliases and resurrection patterns, builds the entity fingerprint
    that all subsequent agents use as input.
    """

    @property
    def module_name(self) -> str:
        return "ghost_tracker"

    async def run(self, fingerprint: EntityFingerprint) -> AgentResponse:
        settings = get_settings()
        name = fingerprint.canonical_name
        self.logger.info(f"Investigating: '{name}'")

        # ── Run all sources concurrently ──────────────────────────────────
        ofac_results, un_results, os_results, corp_results = await asyncio.gather(
            query_ofac(name),
            query_un_sanctions(name),
            query_opensanctions(name, settings),
            query_opencorporates(name, settings),
            return_exceptions=True,  # don't crash if one source fails
        )

        # Normalise — replace exceptions with empty lists
        ofac_results = ofac_results if isinstance(ofac_results, list) else []
        un_results = un_results if isinstance(un_results, list) else []
        os_results = os_results if isinstance(os_results, list) else []
        corp_results = corp_results if isinstance(corp_results, list) else []

        # ── Build evidence items ──────────────────────────────────────────
        evidence: list[EvidenceItem] = []

        # OFAC evidence
        for r in ofac_results:
            evidence.append(EvidenceItem(
                source="OFAC SDN",
                type="sanctions_match",
                detail=(
                    f"OFAC match: '{r['name']}' "
                    f"(matched via '{r['matched_name']}') "
                    f"| Programs: {', '.join(r.get('programs', [])[:3])}"
                ),
                confidence=r["confidence"],
            ))

        # UN evidence
        for r in un_results:
            evidence.append(EvidenceItem(
                source="UN Security Council",
                type="sanctions_match",
                detail=(
                    f"UN Consolidated match: '{r['name']}' "
                    f"[{r.get('type', 'unknown')}] "
                    f"(matched via '{r['matched_name']}')"
                ),
                confidence=r["confidence"],
            ))

        # OpenSanctions evidence
        for r in os_results:
            datasets = r.get("datasets", [])[:2]
            evidence.append(EvidenceItem(
                source="OpenSanctions",
                type="sanctions_match",
                detail=(
                    f"OpenSanctions match: '{r['name']}' "
                    f"| Score: {r['score']:.0%} "
                    f"| Lists: {', '.join(datasets)}"
                ),
                url=r.get("url"),
                confidence=r["confidence"],
            ))

        # OpenCorporates evidence (director overlaps / opacity jurisdictions)
        for r in corp_results:
            detail = (
                f"Corporate match: '{r['name']}' in {r['jurisdiction']} "
                f"| Status: {r.get('status', 'unknown')}"
            )
            if r.get("opacity_jurisdiction"):
                detail += " ⚠️ HIGH-RISK JURISDICTION"

            evidence.append(EvidenceItem(
                source="OpenCorporates",
                type="corporate_match",
                detail=detail,
                url=r.get("url"),
                confidence=r["similarity"],
            ))

        # ── Enrich fingerprint with discovered data ───────────────────────
        enriched = enrich_fingerprint(
            fingerprint, ofac_results, un_results, os_results, corp_results
        )

        # ── Calculate risk score ──────────────────────────────────────────
        sanctions_hit = bool(ofac_results or un_results or os_results)
        top_confidence = max((e.confidence for e in evidence), default=0.0)
        alias_score = min(len(enriched.aliases) / 10, 1.0)
        jurisdiction_score = min(len(enriched.jurisdictions) / 5, 1.0)

        risk_score = min(1.0, (
            (0.50 * top_confidence) +
            (0.25 * (1.0 if sanctions_hit else 0.0)) +
            (0.15 * alias_score) +
            (0.10 * jurisdiction_score)
        ))

        # Sort evidence by confidence descending
        evidence.sort(key=lambda e: e.confidence, reverse=True)

        self.logger.info(
            f"Ghost Tracker complete | "
            f"evidence={len(evidence)} | "
            f"risk={risk_score:.2f} | "
            f"sanctions_hit={sanctions_hit} | "
            f"aliases={len(enriched.aliases)} | "
            f"jurisdictions={len(enriched.jurisdictions)}"
        )

        return AgentResponse(
            module=self.module_name,
            entity_id=fingerprint.entity_id,
            risk_score=round(risk_score, 3),
            evidence=evidence,
            data={
                "fingerprint": enriched.model_dump(),
                "sanctions_hit": sanctions_hit,
                "sanctions_lists": enriched.sanctions_lists,
                "alias_count": len(enriched.aliases),
                "jurisdiction_count": len(enriched.jurisdictions),
                "source_breakdown": {
                    "ofac": len(ofac_results),
                    "un": len(un_results),
                    "opensanctions": len(os_results),
                    "opencorporates": len(corp_results),
                },
            },
        )
