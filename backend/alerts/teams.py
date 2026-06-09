from datetime import datetime
from shared.config import get_settings
from shared.schemas import AlertPayload
from shared.logger import get_logger
from alerts.graph_client import send_graph_message

logger = get_logger(__name__)

def build_adaptive_card(alert: AlertPayload) -> dict:
    """Generate Adaptive Card 1.5 JSON payload for a Teams message."""
    risk_colors = {
        "low": "Good",
        "medium": "Warning",
        "high": "Attention",
        "critical": "Attention"
    }
    color = risk_colors.get(alert.risk_level.value, "Default")
    
    evidence_facts = [{"title": f"Finding {i+1}", "value": str(ev)} for i, ev in enumerate(alert.top_evidence[:3])]
    
    timestamp = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC")
    
    card = {
        "type": "message",
        "attachments": [
            {
                "contentType": "application/vnd.microsoft.card.adaptive",
                "contentUrl": None,
                "content": {
                    "$schema": "http://adaptivecards.io/schemas/adaptive-card.json",
                    "type": "AdaptiveCard",
                    "version": "1.5",
                    "body": [
                        {
                            "type": "TextBlock",
                            "size": "Large",
                            "weight": "Bolder",
                            "text": f"🚨 Shadow Intel Alert: {alert.risk_level.value.upper()}",
                            "color": color
                        },
                        {
                            "type": "FactSet",
                            "facts": [
                                {"title": "Entity:", "value": alert.entity_name},
                                {"title": "Confidence:", "value": f"{alert.confidence * 100:.1f}%"},
                                {"title": "Risk Level:", "value": alert.risk_level.value.upper()},
                                {"title": "Jurisdiction:", "value": alert.jurisdiction or "Unknown"},
                                {"title": "Timestamp:", "value": timestamp}
                            ]
                        },
                        {
                            "type": "TextBlock",
                            "text": "Top Evidence Findings:",
                            "weight": "Bolder",
                            "wrap": True,
                            "spacing": "Medium"
                        },
                        {
                            "type": "FactSet",
                            "facts": evidence_facts
                        }
                    ],
                    "actions": [
                        {
                            "type": "Action.OpenUrl",
                            "title": "View Investigation Report",
                            "url": alert.report_url or f"https://shadowintel.com/investigate/{alert.entity_id}"
                        }
                    ]
                }
            }
        ]
    }
    return card

async def send_teams_alert(alert: AlertPayload) -> bool:
    """Send an adaptive card alert to Teams via Microsoft Graph API."""
    settings = get_settings()
    if not settings.graph_teams_team_id or not settings.graph_teams_channel_id:
        logger.warning("Teams config missing — skipping Teams alert")
        return False
        
    payload = build_adaptive_card(alert)
    logger.info(f"Sending Teams Adaptive Card for: {alert.entity_name}")
    
    return await send_graph_message(
        team_id=settings.graph_teams_team_id,
        channel_id=settings.graph_teams_channel_id,
        payload=payload
    )
