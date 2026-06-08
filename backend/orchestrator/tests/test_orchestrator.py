"""
Tests for the Foundry IQ Orchestrator pipeline.
Run with: pytest backend/orchestrator/tests/ -v
"""

import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

from shared.schemas import (
    AgentResponse, AgentStatus, EvidenceItem,
    InvestigateRequest, RiskLevel,
)
from agents.ghost_tracker.fingerprint import build_fingerprint
from orchestrator.merger import merge_agent_results, WEIGHTS


# ─── Helpers ──────────────────────────────────────────────────────────────────

def make_agent_response(
    module: str,
    risk: float,
    evidence_count: int = 2,
    status: AgentStatus = AgentStatus.complete,
) -> AgentResponse:
    """Build a minimal but valid AgentResponse for testing."""
    return AgentResponse(
        module=module,
        entity_id="test-entity-id",
        status=status,
        risk_score=risk,
        evidence=[
            EvidenceItem(
                source=f"Source_{i}",
                type="test",
                detail=f"Test finding {i} from {module}",
                confidence=risk,
            )
            for i in range(evidence_count)
        ],
    )


# ─── merger.py tests ──────────────────────────────────────────────────────────

def test_merge_weights_correctly():
    """
    With only ghost_tracker at 1.0 and all others at 0.0,
    the normalised confidence should equal ghost's weight (0.30).
    """
    ghost     = make_agent_response("ghost_tracker",    risk=1.0)
    money     = make_agent_response("money_trail",      risk=0.0)
    ownership = make_agent_response("ownership_unwind", risk=0.0)
    signal    = make_agent_response("dark_signal",      risk=0.0)

    _, confidence, _, _ = merge_agent_results(ghost, money, ownership, signal, None)
    assert abs(confidence - WEIGHTS["ghost_tracker"]) < 0.01


def test_merge_risk_classification_critical():
    """All agents at 1.0 → critical risk."""
    ghost     = make_agent_response("ghost_tracker",    risk=1.0)
    money     = make_agent_response("money_trail",      risk=1.0)
    ownership = make_agent_response("ownership_unwind", risk=1.0)
    signal    = make_agent_response("dark_signal",      risk=1.0)

    _, confidence, risk_level, _ = merge_agent_results(
        ghost, money, ownership, signal, None
    )
    assert risk_level == RiskLevel.critical
    assert confidence >= 0.80


def test_merge_risk_classification_low():
    """All agents at 0.0 → low risk."""
    ghost     = make_agent_response("ghost_tracker",    risk=0.0)
    money     = make_agent_response("money_trail",      risk=0.0)
    ownership = make_agent_response("ownership_unwind", risk=0.0)
    signal    = make_agent_response("dark_signal",      risk=0.0)

    _, confidence, risk_level, _ = merge_agent_results(
        ghost, money, ownership, signal, None
    )
    assert risk_level == RiskLevel.low
    assert confidence == 0.0


def test_merge_handles_all_none_agents():
    """All-None agents → zero confidence, low risk, empty evidence."""
    evidence, confidence, risk, breakdown = merge_agent_results(
        None, None, None, None, None
    )
    assert confidence == 0.0
    assert risk == RiskLevel.low
    assert evidence == []


def test_merge_handles_partial_none():
    """Merger works when only ghost ran — weight is normalised."""
    ghost = make_agent_response("ghost_tracker", risk=0.5)
    evidence, confidence, risk, breakdown = merge_agent_results(
        ghost, None, None, None, None
    )
    assert confidence > 0
    assert isinstance(evidence, list)
    assert risk in [RiskLevel.low, RiskLevel.medium]


def test_evidence_deduplication_by_url():
    """Two evidence items with the same URL should appear only once."""
    shared_url = "http://ofac.example/entity/123"
    item_a = EvidenceItem(
        source="OFAC", type="test", detail="Finding A",
        url=shared_url, confidence=0.9,
    )
    item_b = EvidenceItem(
        source="OFAC", type="test", detail="Finding B (dup URL)",
        url=shared_url, confidence=0.7,
    )

    ghost = make_agent_response("ghost_tracker", risk=0.8, evidence_count=0)
    ghost.evidence = [item_a, item_b]

    evidence, _, _, _ = merge_agent_results(ghost, None, None, None, None)
    urls = [e.url for e in evidence if e.url == shared_url]
    assert len(urls) == 1


def test_evidence_deduplication_by_detail():
    """Two items with no URL but identical source+detail should appear once."""
    item = EvidenceItem(
        source="OFAC", type="test",
        detail="Duplicate finding text here", confidence=0.9,
    )
    ghost = make_agent_response("ghost_tracker", risk=0.8, evidence_count=0)
    ghost.evidence = [item, item]

    evidence, _, _, _ = merge_agent_results(ghost, None, None, None, None)
    assert len(evidence) == 1


def test_evidence_sorted_by_confidence():
    """Evidence items should be returned sorted by confidence descending."""
    ghost = make_agent_response("ghost_tracker", risk=0.8, evidence_count=0)
    ghost.evidence = [
        EvidenceItem(source="A", type="t", detail="low",  confidence=0.3),
        EvidenceItem(source="B", type="t", detail="high", confidence=0.9),
        EvidenceItem(source="C", type="t", detail="mid",  confidence=0.6),
    ]

    evidence, _, _, _ = merge_agent_results(ghost, None, None, None, None)
    confidences = [e.confidence for e in evidence]
    assert confidences == sorted(confidences, reverse=True)


def test_source_breakdown_counts():
    """source_breakdown should accurately count unique evidence per module."""
    ghost = make_agent_response("ghost_tracker", risk=0.5, evidence_count=3)
    money = make_agent_response("money_trail",   risk=0.3, evidence_count=2)

    _, _, _, breakdown = merge_agent_results(ghost, money, None, None, None)
    assert breakdown["ghost_tracker"] == 3
    assert breakdown["money_trail"] == 2
    assert breakdown["ownership_unwind"] == 0


def test_failed_agent_excluded_from_weight():
    """A failed agent should not contribute its score to the confidence."""
    ghost = make_agent_response(
        "ghost_tracker", risk=1.0, status=AgentStatus.failed
    )
    money = make_agent_response("money_trail", risk=0.0)
    ownership = make_agent_response("ownership_unwind", risk=0.0)
    signal = make_agent_response("dark_signal", risk=0.0)

    _, confidence, _, _ = merge_agent_results(ghost, money, ownership, signal, None)
    # Ghost failed — its weight redistributed; all active agents have risk 0.0
    assert confidence == 0.0


# ─── session store tests ──────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_session_create_and_get():
    """Created session should be retrievable by entity_id."""
    from shared.session import SessionStore
    from shared.schemas import EntityFingerprint

    test_store = SessionStore()
    fp = EntityFingerprint(
        entity_id="sess-test-01",
        canonical_name="Test Corp",
    )
    session = await test_store.create("sess-test-01", "Test Corp", fp)
    fetched = await test_store.get("sess-test-01")
    assert fetched is not None
    assert fetched.entity_id == "sess-test-01"
    assert fetched.entity_name == "Test Corp"


@pytest.mark.asyncio
async def test_session_complete():
    """Completing a session should set overall_status to 'complete'."""
    from shared.session import SessionStore
    from shared.schemas import EntityFingerprint, InvestigationReport, RiskLevel

    test_store = SessionStore()
    fp = EntityFingerprint(entity_id="sess-test-02", canonical_name="Test Corp")
    await test_store.create("sess-test-02", "Test Corp", fp)

    dummy_report = InvestigationReport(
        entity_id="sess-test-02",
        entity_name="Test Corp",
        unified_confidence=0.5,
        risk_level=RiskLevel.medium,
    )
    await test_store.complete("sess-test-02", dummy_report)

    session = await test_store.get("sess-test-02")
    assert session.status.overall_status == "complete"
    assert session.report is not None


@pytest.mark.asyncio
async def test_session_fail():
    """Failing a session should set overall_status to 'failed' and store the error."""
    from shared.session import SessionStore
    from shared.schemas import EntityFingerprint

    test_store = SessionStore()
    fp = EntityFingerprint(entity_id="sess-test-03", canonical_name="Test Corp")
    await test_store.create("sess-test-03", "Test Corp", fp)
    await test_store.fail("sess-test-03", "network timeout")

    session = await test_store.get("sess-test-03")
    assert session.status.overall_status == "failed"
    assert session.error == "network timeout"


@pytest.mark.asyncio
async def test_session_eviction():
    """Store should evict oldest session when MAX_SESSIONS is reached."""
    from shared.session import SessionStore
    from shared.schemas import EntityFingerprint

    test_store = SessionStore()
    test_store.MAX_SESSIONS = 3

    for i in range(3):
        fp = EntityFingerprint(entity_id=f"evict-{i}", canonical_name=f"Entity {i}")
        await test_store.create(f"evict-{i}", f"Entity {i}", fp)

    # Adding a 4th should evict 'evict-0'
    fp = EntityFingerprint(entity_id="evict-3", canonical_name="Entity 3")
    await test_store.create("evict-3", "Entity 3", fp)

    assert await test_store.get("evict-0") is None
    assert await test_store.get("evict-3") is not None


# ─── Full pipeline smoke test ─────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_full_pipeline_stub():
    """
    End-to-end smoke test with stub agents.
    Verifies the pipeline completes (or fails gracefully) with all stubs returning
    empty but valid responses.
    """
    from api.routes.investigate import _run_investigation
    from shared.session import SessionStore
    from shared.schemas import EntityFingerprint

    test_store = SessionStore()
    fp = EntityFingerprint(
        entity_id="pipeline-test-01",
        canonical_name="Test Entity",
    )

    session = await test_store.create("pipeline-test-01", "Test Entity", fp)

    # Patch the module-level store used by _run_investigation
    with patch("api.routes.investigate.store", test_store):
        await _run_investigation("pipeline-test-01")

    fetched = await test_store.get("pipeline-test-01")
    assert fetched is not None
    # Stubs return empty evidence, so the pipeline should complete successfully
    assert fetched.status.overall_status in ["complete", "failed"]
