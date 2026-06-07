from shared.http_client import get_json
from shared.logger import get_logger

logger = get_logger(__name__)


async def query_opensanctions(name: str, settings) -> list[dict]:
    """Query OpenSanctions API for entity name matches."""
    if not settings.opensanctions_api_key:
        logger.warning("No OpenSanctions API key configured — skipping")
        return []

    url = "https://api.opensanctions.org/match/default"
    headers = {"Authorization": f"ApiKey {settings.opensanctions_api_key}"}
    payload = {
        "queries": {
            "entity": {
                "schema": "Thing",
                "properties": {"name": [name]}
            }
        }
    }

    # TODO: implement actual POST request and parse results
    # Stub: return empty list until implemented
    logger.info(f"Querying OpenSanctions for: {name}")
    return []
