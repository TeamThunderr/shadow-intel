from azure.identity.aio import ClientSecretCredential
from msgraph import GraphServiceClient
from shared.config import get_settings
from shared.logger import get_logger
import time

logger = get_logger(__name__)

_token_cache: dict[str, dict] = {}

async def _get_credential() -> ClientSecretCredential:
    settings = get_settings()
    return ClientSecretCredential(
        tenant_id=settings.graph_tenant_id,
        client_id=settings.graph_client_id,
        client_secret=settings.graph_client_secret,
    )

async def get_access_token() -> str:
    """Get access token, returning from cache if valid."""
    settings = get_settings()
    
    # Check cache
    if "graph" in _token_cache:
        cached = _token_cache["graph"]
        if time.time() < cached["expires_on"]:
            return cached["token"]
            
    return await refresh_access_token()

async def refresh_access_token() -> str:
    """Fetch a new access token and update cache."""
    settings = get_settings()
    
    if not settings.graph_client_id or not settings.graph_client_secret:
        logger.warning("Graph API credentials missing")
        return ""
        
    try:
        cred = await _get_credential()
        token_info = await cred.get_token("https://graph.microsoft.com/.default")
        
        _token_cache["graph"] = {
            "token": token_info.token,
            "expires_on": token_info.expires_on - 300 # refresh 5 minutes early
        }
        
        logger.info("Graph access token refreshed successfully.")
        return token_info.token
    except Exception as e:
        logger.error(f"Failed to refresh Graph token: {e}")
        return ""

def get_graph_client() -> GraphServiceClient:
    """Return a configured GraphServiceClient using the async credential."""
    settings = get_settings()
    from azure.identity import ClientSecretCredential as SyncCredential
    
    # msgraph-sdk uses sync credential initialization
    credential = SyncCredential(
        tenant_id=settings.graph_tenant_id,
        client_id=settings.graph_client_id,
        client_secret=settings.graph_client_secret,
    )
    return GraphServiceClient(credentials=credential)
