from shared.logger import get_logger

logger = get_logger(__name__)

ICIJ_SEARCH_URL = "https://offshoreleaks.icij.org/api/search"


async def search_icij(name: str) -> list[dict]:
    """
    Search ICIJ Offshore Leaks database (Panama Papers, Pandora Papers, etc.)
    Data is cached in Fabric lakehouse for performance.
    """
    # TODO: query Fabric-cached ICIJ dataset
    logger.info(f"Searching ICIJ for: {name}")
    return []
