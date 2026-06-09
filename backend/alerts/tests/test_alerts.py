import pytest
from unittest.mock import AsyncMock, patch
from datetime import datetime
from shared.schemas import AlertPayload, RiskLevel
from alerts.priority import route_alert, determine_alert_priority
from alerts.teams import build_adaptive_card
from alerts.outlook import build_email_alert
from alerts.pipeline import process_alert

@pytest.fixture
def mock_alert():
    return AlertPayload(
        entity_id="test-123",
        entity_name="Test Entity",
        match_event="New Company Registered",
        confidence=0.95,
        jurisdiction="Panama",
        risk_level=RiskLevel.critical,
        top_evidence=["Evidence 1", "Evidence 2", "Evidence 3"],
        report_url="http://test",
        timestamp=datetime.utcnow()
    )

def test_priority_engine():
    assert determine_alert_priority(0.20) == RiskLevel.low
    assert determine_alert_priority(0.50) == RiskLevel.medium
    assert determine_alert_priority(0.80) == RiskLevel.high
    assert determine_alert_priority(0.95) == RiskLevel.critical

def test_routing_logic(mock_alert):
    mock_alert.confidence = 0.95
    routing = route_alert(mock_alert)
    assert routing["send_teams"] is True
    assert routing["send_email"] is True
    assert routing["is_priority"] is True
    assert routing["log_only"] is False

    mock_alert.confidence = 0.30
    routing = route_alert(mock_alert)
    assert routing["send_teams"] is False
    assert routing["send_email"] is False
    assert routing["log_only"] is True

def test_adaptive_card_composer(mock_alert):
    card = build_adaptive_card(mock_alert)
    assert card["type"] == "message"
    assert card["attachments"][0]["content"]["version"] == "1.5"
    
    # Verify entity name is in the card
    facts = card["attachments"][0]["content"]["body"][1]["facts"]
    entity_fact = next(f for f in facts if f["title"] == "Entity:")
    assert entity_fact["value"] == "Test Entity"

def test_email_composer(mock_alert):
    html = build_email_alert(mock_alert)
    assert "Test Entity" in html
    assert "CRITICAL" in html
    assert "95.0%" in html
    assert "Evidence 1" in html

@pytest.mark.asyncio
@patch("alerts.pipeline.write_alert_log", new_callable=AsyncMock)
@patch("alerts.pipeline.update_alert_status", new_callable=AsyncMock)
@patch("alerts.pipeline.send_teams_alert", new_callable=AsyncMock)
@patch("alerts.pipeline.send_outlook_alert", new_callable=AsyncMock)
async def test_delivery_pipeline_success(mock_outlook, mock_teams, mock_update, mock_write, mock_alert):
    mock_write.return_value = "alert-123"
    mock_teams.return_value = True
    mock_outlook.return_value = True

    results = await process_alert(mock_alert, analyst_email="analyst@test.com")

    assert results["teams_success"] is True
    assert results["email_success"] is True
    assert results["overall_status"] == "delivered"
    
    mock_teams.assert_called_once()
    mock_outlook.assert_called_once()
    mock_update.assert_called_with("alert-123", "delivered")

@pytest.mark.asyncio
@patch("alerts.pipeline.write_alert_log", new_callable=AsyncMock)
@patch("alerts.pipeline.update_alert_status", new_callable=AsyncMock)
@patch("alerts.pipeline.send_teams_alert", new_callable=AsyncMock)
@patch("alerts.pipeline.send_outlook_alert", new_callable=AsyncMock)
async def test_delivery_pipeline_partial_failure(mock_outlook, mock_teams, mock_update, mock_write, mock_alert):
    mock_write.return_value = "alert-123"
    # Mock Teams failing, but Outlook succeeding
    mock_teams.return_value = False
    mock_outlook.return_value = True

    results = await process_alert(mock_alert, analyst_email="analyst@test.com")

    assert results["teams_success"] is False
    assert results["email_success"] is True
    assert results["overall_status"] == "partial_failure"
    
    mock_update.assert_called_with("alert-123", "partial_failure")
