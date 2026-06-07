from shared.logger import get_logger

logger = get_logger(__name__)


async def query_un_sanctions(name: str) -> list[dict]:
    """
    Query UN Consolidated Sanctions list.
    List is cached in Fabric — see fabric/pipelines/opensanctions.py
    """
    # TODO: query Fabric lakehouse for UN sanctions data
    logger.info(f"Querying UN Sanctions for: {name}")
    return []
