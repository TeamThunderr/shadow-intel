"""
Agent result merger and unified confidence scoring.
Combines output from all 5 Shadow Intel agents into a single evidence set
and calculates the weighted confidence score used throughout the report.
"""

from shared.schemas import AgentResponse, EvidenceItem, RiskLevel, AgentStatus
from shared.logger import get_logger

logger = get_logger(__name__)

# ─── Weighting model ──────────────────────────────────────────────────────────
# Weights must sum to 1.0.
# Ghost Tracker and Money Trail carry the most weight because they query
# authoritative primary sources (government sanctions lists, blockchain ledgers).
# Dark Signal is corroborative OSINT — valuable but less definitive.
WEIGHTS: dict[str, float] = {
    "ghost_tracker":    0.30,
    "money_trail":      0.25,
    "ownership_unwind": 0.25,
    "dark_signal":      0.20,
}

# Risk bands (descending order — first match wins)
RISK_BANDS: list[tuple[RiskLevel, float]] = [
    (RiskLevel.critical, 0.80),
    (RiskLevel.high,     0.60),
    (RiskLevel.medium,   0.40),
    (RiskLevel.low,      0.00),
]


def merge_agent_results(
    ghost:     AgentResponse | None,
    money:     AgentResponse | None,
    ownership: AgentResponse | None,
    signal:    AgentResponse | None,
    resurface: AgentResponse | None,
) -> tuple[list[EvidenceItem], float, RiskLevel, dict]:
    """
    Merge evidence from all 5 agents into a deduplicated evidence set.
    Calculate a weighted confidence score and classify the risk level.

    Returns:
        merged_evidence   — deduplicated, confidence-sorted EvidenceItems
        unified_confidence — float [0.0, 1.0]
        risk_level        — RiskLevel enum
        source_breakdown  — dict mapping module_name → evidence count
    """
    agent_map: dict[str, AgentResponse | None] = {
        "ghost_tracker":    ghost,
        "money_trail":      money,
        "ownership_unwind": ownership,
        "dark_signal":      signal,
        "resurface_engine": resurface,
    }

    # ── Deduplicate and collect evidence ──────────────────────────────────
    all_evidence: list[EvidenceItem] = []
    seen: set[str] = set()
    source_breakdown: dict[str, int] = {}

    for module_name, agent in agent_map.items():
        count = 0
        if agent and agent.evidence:
            for item in agent.evidence:
                # Prefer URL as dedup key; fall back to first 80 chars of detail
                dedup_key = item.url or f"{item.source}:{item.detail[:80]}"
                if dedup_key not in seen:
                    all_evidence.append(item)
                    seen.add(dedup_key)
                    count += 1
        source_breakdown[module_name] = count

    # ── Weighted confidence score ──────────────────────────────────────────
    # Weight normalisation: if an agent failed we redistribute its weight
    # proportionally across the agents that did run, so the score remains
    # on the [0, 1] scale regardless of how many agents complete.
    weighted_sum = 0.0
    active_weight = 0.0

    for module_name, weight in WEIGHTS.items():
        agent = agent_map.get(module_name)
        if agent and agent.status != AgentStatus.failed:
            weighted_sum += agent.risk_score * weight
            active_weight += weight

    if active_weight > 0:
        unified_confidence = weighted_sum / active_weight
    else:
        unified_confidence = 0.0

    # ── Resurface bonus ────────────────────────────────────────────────────
    # If the Resurface Engine found active new registrations matching the
    # fingerprint, add a small bonus (max +5 pp) — it indicates the entity
    # is actively trying to re-emerge, which elevates urgency.
    if resurface and resurface.risk_score > 0.50:
        bonus = resurface.risk_score * 0.05
        unified_confidence = min(1.0, unified_confidence + bonus)

    unified_confidence = round(min(1.0, max(0.0, unified_confidence)), 3)

    # ── Risk classification ────────────────────────────────────────────────
    risk_level = RiskLevel.low
    for level, threshold in RISK_BANDS:
        if unified_confidence >= threshold:
            risk_level = level
            break

    # ── Sort evidence by confidence descending ─────────────────────────────
    all_evidence.sort(key=lambda e: e.confidence, reverse=True)

    logger.info(
        f"Merge complete | "
        f"evidence_total={len(all_evidence)} | "
        f"confidence={unified_confidence:.3f} | "
        f"risk={risk_level.value} | "
        f"sources={source_breakdown}"
    )

    return all_evidence, unified_confidence, risk_level, source_breakdown


def get_agent_summary(agent: AgentResponse | None, module_name: str) -> dict:
    """Return a clean summary dict for a single agent — used in logging and UI."""
    if not agent:
        return {"module": module_name, "status": "not_run", "risk_score": 0.0, "evidence_count": 0}
    return {
        "module": module_name,
        "status": agent.status.value,
        "risk_score": agent.risk_score,
        "evidence_count": len(agent.evidence),
        "processing_time_ms": agent.processing_time_ms,
        "error": agent.error,
    }
