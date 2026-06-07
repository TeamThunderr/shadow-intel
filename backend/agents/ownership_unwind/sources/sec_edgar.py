from shared.http_client import get_json
from shared.logger import get_logger

logger = get_logger(__name__)

EDGAR_BASE = "https://efts.sec.gov/LATEST/search-index"


async def search_edgar(entity_name: str) -> list[dict]:
    """
    Search SEC EDGAR full-text search for entity name.
    Returns matching filings with company information.
    """
    url = "https://efts.sec.gov/LATEST/search-index?q=%22{}%22&dateRange=custom".format(
        entity_name.replace(" ", "+")
    )

    # TODO: parse EDGAR response and extract ownership/UBO data
    logger.info(f"Querying SEC EDGAR for: {entity_name}")
    return []


async def get_beneficial_owners(cik: str) -> list[dict]:
    """
    Retrieve Schedule 13D/13G beneficial ownership filings for a given CIK.
    """
    # TODO: query EDGAR filings API
    return []
