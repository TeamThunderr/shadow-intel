from shared.logger import get_logger

logger = get_logger(__name__)


async def query_ofac(name: str) -> list[dict]:
    """
    Query OFAC SDN list for entity name matches.
    OFAC list is downloaded daily and stored in Fabric.
    Uses Fabric client to query — see fabric/client.py
    """
    # TODO: integrate with fabric/client.py to query cached OFAC data
    logger.info(f"Querying OFAC for: {name}")
    return []
