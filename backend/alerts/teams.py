from msgraph import GraphServiceClient
from msgraph.generated.teams.item.channels.item.messages.messages_request_builder import (
    MessagesRequestBuilder,
)
from msgraph.generated.models.chat_message import ChatMessage
from msgraph.generated.models.item_body import ItemBody
from azure.identity import ClientSecretCredential
from shared.config import get_settings
from shared.schemas import AlertPayload
from shared.logger import get_logger

logger = get_logger(__name__)


def _get_graph_client() -> GraphServiceClient:
    settings = get_settings()
    credential = ClientSecretCredential(
        tenant_id=settings.graph_tenant_id,
        client_id=settings.graph_client_id,
        client_secret=settings.graph_client_secret,
    )
    return GraphServiceClient(credentials=credential)


async def send_teams_alert(alert: AlertPayload) -> bool:
    """
    Send a Shadow Intel alert to a Microsoft Teams channel.
    Uses Microsoft Graph API (Work IQ).
    """
    settings = get_settings()
    if not settings.graph_teams_team_id or not settings.graph_teams_channel_id:
        logger.warning("Teams config missing — skipping Teams alert")
        return False

    risk_emoji = {"low": "🟢", "medium": "🟡", "high": "🟠", "critical": "🔴"}.get(
        alert.risk_level.value, "⚪"
    )

    message_html = f"""
<b>{risk_emoji} Shadow Intel Alert — {alert.risk_level.value.upper()}</b><br>
<b>Entity:</b> {alert.entity_name}<br>
<b>Event:</b> {alert.match_event}<br>
<b>Confidence:</b> {alert.confidence * 100:.1f}%<br>
<b>Jurisdiction:</b> {alert.jurisdiction or 'Unknown'}<br>
<b>Top Evidence:</b><br>
{'<br>'.join(f'• {e}' for e in alert.top_evidence[:3])}<br>
<a href="{alert.report_url}">View Full Report</a>
"""

    try:
        client = _get_graph_client()
        message = ChatMessage(body=ItemBody(content=message_html, content_type="html"))
        await client.teams.by_team_id(settings.graph_teams_team_id)\
            .channels.by_channel_id(settings.graph_teams_channel_id)\
            .messages.post(message)
        logger.info(f"Teams alert sent for entity: {alert.entity_name}")
        return True
    except Exception as e:
        logger.error(f"Teams alert failed: {e}")
        return False
