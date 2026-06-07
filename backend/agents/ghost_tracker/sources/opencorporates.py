from shared.http_client import get_json
from shared.logger import get_logger

logger = get_logger(__name__)


async def query_opencorporates(name: str, settings) -> list[dict]:
    """Search OpenCorporates for similar company names across jurisdictions."""
    if not settings.opencorporates_api_key:
        logger.warning("No OpenCorporates API key — skipping")
        return []

    url = "https://api.opencorporates.com/v0.4/companies/search"
    params = {
        "q": name,
        "api_token": settings.opencorporates_api_key,
        "per_page": 10,
    }

    # TODO: parse response and return structured list
    logger.info(f"Querying OpenCorporates for: {name}")
    return []
