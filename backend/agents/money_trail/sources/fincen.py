from shared.logger import get_logger

logger = get_logger(__name__)


async def query_fincen(entity_name: str) -> list[dict]:
    """
    Cross-reference entity against FinCEN public SAR data.
    FinCEN suspicious activity report data is publicly available.
    """
    # TODO: query FinCEN public dataset stored in Fabric lakehouse
    logger.info(f"Querying FinCEN for: {entity_name}")
    return []
