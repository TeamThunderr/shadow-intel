from fabric.client import get_fabric_client
from shared.http_client import get_json
from shared.logger import get_logger

logger = get_logger(__name__)

GLEIF_DOWNLOAD_URL = "https://leilookup.gleif.org/api/v2/fuzzycompletions"


async def ingest_gleif():
    """
    Download GLEIF (Global LEI Foundation) entity data and store in Fabric.
    GLEIF provides Legal Entity Identifiers for financial institutions globally.
    """
    logger.info("Starting GLEIF ingestion pipeline")
    client = get_fabric_client()

    # TODO: download full LEI dataset, parse, store in Fabric
    logger.info("GLEIF pipeline stub — implement download and Fabric write")
