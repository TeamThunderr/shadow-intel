from shared.http_client import get_json
from shared.logger import get_logger
from shared.config import get_settings

logger = get_logger(__name__)

OCCRP_BASE = "https://aleph.occrp.org/api/2"


async def search_occrp(name: str) -> list[dict]:
    """
    Query OCCRP Aleph investigative database for entity mentions.
    Aleph contains leaked documents, court records, and corporate registries.
    """
    settings = get_settings()
    if not settings.occrp_api_key:
        logger.warning("No OCCRP API key — skipping")
        return []

    url = f"{OCCRP_BASE}/search"
    params = {"q": name, "limit": 20}
    headers = {"Authorization": f"ApiKey {settings.occrp_api_key}"}

    # TODO: parse response and extract entity mentions
    logger.info(f"Querying OCCRP Aleph for: {name}")
    return []
