from shared.http_client import get_json
from shared.logger import get_logger
from shared.config import get_settings

logger = get_logger(__name__)

COMPANIES_HOUSE_BASE = "https://api.company-information.service.gov.uk"


async def search_company(name: str) -> list[dict]:
    """Search Companies House for a company by name."""
    settings = get_settings()
    if not settings.companies_house_api_key:
        logger.warning("No Companies House API key — skipping")
        return []

    url = f"{COMPANIES_HOUSE_BASE}/search/companies"
    params = {"q": name, "items_per_page": 10}
    headers = {}  # Basic auth handled via API key as username

    # TODO: implement Basic auth and parse response
    logger.info(f"Querying Companies House for: {name}")
    return []


async def get_officers(company_number: str) -> list[dict]:
    """Get officers/directors for a Companies House company number."""
    # TODO: query /company/{company_number}/officers
    return []
