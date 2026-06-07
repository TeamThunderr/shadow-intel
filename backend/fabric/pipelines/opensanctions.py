from fabric.client import get_fabric_client
from shared.http_client import get_json
from shared.logger import get_logger

logger = get_logger(__name__)

OPENSANCTIONS_EXPORT_URL = "https://data.opensanctions.org/datasets/latest/default/entities.ftm.json"


async def ingest_opensanctions():
    """
    Download OpenSanctions bulk export and store in Fabric Lakehouse.
    Scheduled to run daily. Stores as delta table for fast fuzzy lookup.
    """
    logger.info("Starting OpenSanctions ingestion pipeline")
    client = get_fabric_client()

    # TODO: stream download, parse FtM JSON, batch write to Fabric
    logger.info("OpenSanctions pipeline stub — implement streaming ingest")
