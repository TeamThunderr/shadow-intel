import httpx
import asyncio
from typing import Optional
from shared.logger import get_logger
from alerts.graph_auth import get_access_token

logger = get_logger(__name__)

async def post_graph_request(endpoint: str, payload: dict, retries: int = 3) -> Optional[dict]:
    """Make an authenticated POST request to Microsoft Graph with retries."""
    url = f"https://graph.microsoft.com/v1.0/{endpoint.lstrip('/')}"
    
    for attempt in range(1, retries + 1):
        token = await get_access_token()
        if not token:
            logger.error("No access token available for Graph API.")
            return None
            
        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json"
        }
        
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(url, json=payload, headers=headers, timeout=10.0)
                response.raise_for_status()
                return response.json() if response.content else {}
        except httpx.HTTPStatusError as e:
            logger.warning(f"Graph API HTTP Error on attempt {attempt}: {e.response.status_code} - {e.response.text}")
            if e.response.status_code in [401, 403, 429, 500, 502, 503, 504]:
                if attempt == retries:
                    logger.error(f"Graph request failed permanently after {retries} attempts.")
                    return None
                await asyncio.sleep(2 ** attempt) # Exponential backoff
            else:
                return None
        except httpx.RequestError as e:
            logger.warning(f"Graph API Request Error on attempt {attempt}: {e}")
            if attempt == retries:
                logger.error(f"Graph request failed permanently after {retries} attempts.")
                return None
            await asyncio.sleep(2 ** attempt)

    return None

async def send_graph_message(team_id: str, channel_id: str, payload: dict) -> bool:
    """Send a message/adaptive card to a Teams channel."""
    endpoint = f"/teams/{team_id}/channels/{channel_id}/messages"
    res = await post_graph_request(endpoint, payload)
    return res is not None

async def send_graph_mail(sender_email: str, recipient_email: str, subject: str, html_body: str) -> bool:
    """Send an email via a specific sender."""
    endpoint = f"/users/{sender_email}/sendMail"
    
    payload = {
        "message": {
            "subject": subject,
            "body": {
                "contentType": "HTML",
                "content": html_body
            },
            "toRecipients": [
                {
                    "emailAddress": {
                        "address": recipient_email
                    }
                }
            ]
        },
        "saveToSentItems": "false"
    }
    
    res = await post_graph_request(endpoint, payload)
    return res is not None
