from shared.http_client import get_json
from shared.logger import get_logger

logger = get_logger(__name__)

OPENOWNERSHIP_BASE = "https://register.openownership.org/api"


async def query_openownership(entity_name: str) -> list[dict]:
    """
    Query OpenOwnership register for beneficial ownership data.
    Returns structured ownership chain data.
    """
    # TODO: implement search + ownership traversal
    logger.info(f"Querying OpenOwnership for: {entity_name}")
    return []
