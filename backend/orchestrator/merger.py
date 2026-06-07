from shared.schemas import AgentResponse, EvidenceItem, RiskLevel


def merge_agent_results(
    ghost: AgentResponse | None,
    money: AgentResponse | None,
    ownership: AgentResponse | None,
    signal: AgentResponse | None,
    resurface: AgentResponse | None,
) -> tuple[list[EvidenceItem], float, RiskLevel]:
    """
    Merge evidence from all agents.
    Calculate unified confidence score.
    Classify risk level.
    Returns: (merged_evidence, unified_confidence, risk_level)
    """
    all_evidence: list[EvidenceItem] = []
    seen_urls: set[str] = set()

    for agent in [ghost, money, ownership, signal, resurface]:
        if agent and agent.evidence:
            for item in agent.evidence:
                key = item.url or item.detail
                if key not in seen_urls:
                    all_evidence.append(item)
                    seen_urls.add(key)

    # Weighted confidence formula
    ghost_score = ghost.risk_score if ghost else 0.0
    money_score = money.risk_score if money else 0.0
    ownership_score = ownership.risk_score if ownership else 0.0
    signal_score = signal.risk_score if signal else 0.0

    unified = (
        ghost_score * 0.30 +
        money_score * 0.25 +
        ownership_score * 0.25 +
        signal_score * 0.20
    )

    # Risk classification
    if unified >= 0.80:
        risk = RiskLevel.critical
    elif unified >= 0.60:
        risk = RiskLevel.high
    elif unified >= 0.40:
        risk = RiskLevel.medium
    else:
        risk = RiskLevel.low

    return all_evidence, round(unified, 3), risk
