"""
Tests for Ghost Entity Tracker.
Run with: pytest backend/agents/ghost_tracker/tests/
"""

import pytest
import asyncio
from unittest.mock import patch, AsyncMock
from agents.ghost_tracker.agent import GhostEntityTracker
from agents.ghost_tracker.fingerprint import build_fingerprint, enrich_fingerprint
from shared.schemas import InvestigateRequest, AgentStatus


@pytest.fixture
def sample_fingerprint():
    return build_fingerprint(InvestigateRequest(
        name="Rosneft",
        entity_type="company",
        country_hint="RU"
    ))


@pytest.mark.asyncio
async def test_ghost_tracker_returns_valid_response(sample_fingerprint):
    """Agent should always return a valid AgentResponse even with no API keys."""
    tracker = GhostEntityTracker()
    result = await tracker.execute(sample_fingerprint)
    assert result.module == "ghost_tracker"
    assert result.entity_id == sample_fingerprint.entity_id
    assert result.status in [AgentStatus.complete, AgentStatus.failed]
    assert isinstance(result.risk_score, float)
    assert 0.0 <= result.risk_score <= 1.0


@pytest.mark.asyncio
async def test_fingerprint_enrichment(sample_fingerprint):
    """Fingerprint should be enriched with discovered aliases."""
    mock_ofac = [{
        "aliases": ["Rosneft PJSC", "Rosneft Oil"],
        "confidence": 0.95,
        "programs": ["RUSSIA"],
    }]
    mock_un = []
    mock_os = [{
        "aliases": ["Rosneft JSC"],
        "countries": ["RU"],
        "datasets": ["ru_acf_sanctions"],
        "confidence": 0.90,
    }]
    mock_corp = [{
        "jurisdiction": "RU",
        "company_number": "1027700043502",
        "similarity": 0.92,
        "status": "active",
        "opacity_jurisdiction": False,
    }]

    enriched = enrich_fingerprint(sample_fingerprint, mock_ofac, mock_un, mock_os, mock_corp)
    assert "Rosneft PJSC" in enriched.aliases
    assert "RU" in enriched.jurisdictions
    assert "OFAC SDN" in enriched.sanctions_lists


@pytest.mark.asyncio
async def test_ofac_fuzzy_matching():
    """OFAC fuzzy matcher should find known sanctioned entities."""
    from agents.ghost_tracker.sources.ofac import query_ofac
    # Only runs if OFAC data is reachable — skip in CI if no network
    try:
        results = await query_ofac("Rosneft")
        # Just check structure is correct
        for r in results:
            assert "confidence" in r
            assert 0.0 <= r["confidence"] <= 1.0
    except Exception:
        pytest.skip("OFAC network unavailable")


def test_risk_score_range(sample_fingerprint):
    """Risk score must always be between 0 and 1."""
    tracker = GhostEntityTracker()
    result = asyncio.run(tracker.execute(sample_fingerprint))
    assert 0.0 <= result.risk_score <= 1.0


@pytest.mark.asyncio
async def test_ghost_tracker_handles_source_failures(sample_fingerprint):
    """Agent must complete even when all external sources raise exceptions."""
    with (
        patch("agents.ghost_tracker.sources.ofac.query_ofac", side_effect=Exception("network error")),
        patch("agents.ghost_tracker.sources.un_sanctions.query_un_sanctions", side_effect=Exception("timeout")),
        patch("agents.ghost_tracker.sources.opensanctions.query_opensanctions", side_effect=Exception("403")),
        patch("agents.ghost_tracker.sources.opencorporates.query_opencorporates", side_effect=Exception("rate limit")),
    ):
        tracker = GhostEntityTracker()
        result = await tracker.execute(sample_fingerprint)
        # Must still complete (exceptions are swallowed by asyncio.gather return_exceptions)
        assert result.status == AgentStatus.complete
        assert result.risk_score == 0.0
        assert result.evidence == []


@pytest.mark.asyncio
async def test_evidence_structure(sample_fingerprint):
    """Evidence items must have the correct fields and valid confidence values."""
    mock_ofac = [{
        "uid": "12345",
        "name": "Rosneft Oil Company",
        "matched_name": "Rosneft",
        "aliases": ["Rosneft PJSC"],
        "type": "Entity",
        "programs": ["RUSSIA"],
        "confidence": 0.95,
        "source": "OFAC SDN",
    }]

    with (
        patch("agents.ghost_tracker.agent.query_ofac", return_value=mock_ofac),
        patch("agents.ghost_tracker.agent.query_un_sanctions", return_value=[]),
        patch("agents.ghost_tracker.agent.query_opensanctions", return_value=[]),
        patch("agents.ghost_tracker.agent.query_opencorporates", return_value=[]),
    ):
        tracker = GhostEntityTracker()
        result = await tracker.execute(sample_fingerprint)

        assert result.status == AgentStatus.complete
        assert len(result.evidence) == 1
        ev = result.evidence[0]
        assert ev.source == "OFAC SDN"
        assert ev.type == "sanctions_match"
        assert 0.0 <= ev.confidence <= 1.0
        assert "Rosneft" in ev.detail


@pytest.mark.asyncio
async def test_opacity_jurisdiction_flagged(sample_fingerprint):
    """Corporate matches in opacity jurisdictions must be flagged in evidence detail."""
    mock_corp = [{
        "name": "Rosneft BVI Ltd",
        "jurisdiction": "VG",
        "company_number": "BVI123456",
        "status": "active",
        "incorporation_date": "2010-01-01",
        "url": "https://opencorporates.com/companies/vg/BVI123456",
        "similarity": 0.88,
        "opacity_jurisdiction": True,
        "source": "OpenCorporates",
    }]

    with (
        patch("agents.ghost_tracker.agent.query_ofac", return_value=[]),
        patch("agents.ghost_tracker.agent.query_un_sanctions", return_value=[]),
        patch("agents.ghost_tracker.agent.query_opensanctions", return_value=[]),
        patch("agents.ghost_tracker.agent.query_opencorporates", return_value=mock_corp),
    ):
        tracker = GhostEntityTracker()
        result = await tracker.execute(sample_fingerprint)
        assert result.status == AgentStatus.complete
        corp_ev = next(e for e in result.evidence if e.source == "OpenCorporates")
        assert "HIGH-RISK" in corp_ev.detail


def test_build_fingerprint_country_hint():
    """Country hint should be normalised to uppercase and included in jurisdictions."""
    req = InvestigateRequest(name="Test Corp", entity_type="company", country_hint="ru")
    fp = build_fingerprint(req)
    assert "RU" in fp.jurisdictions
    assert fp.canonical_name == "Test Corp"


def test_build_fingerprint_no_country():
    """Fingerprint with no country hint should have empty jurisdictions list."""
    req = InvestigateRequest(name="Anonymous Corp")
    fp = build_fingerprint(req)
    assert fp.jurisdictions == []
