from fabric.client import get_fabric_client
from shared.http_client import get_json
from shared.logger import get_logger

logger = get_logger(__name__)

OFAC_SDN_URL = "https://www.treasury.gov/ofac/downloads/sdn.xml"
OFAC_CONSOLIDATED_URL = "https://www.treasury.gov/ofac/downloads/consolidated/consolidated.xml"


async def ingest_ofac_sdn():
    """
    Download the OFAC SDN list and store in Fabric Lakehouse.
    Scheduled to run daily via APScheduler.
    """
    logger.info("Starting OFAC SDN ingestion pipeline")
    client = get_fabric_client()

    # TODO: download XML, parse, convert to rows, write to Fabric
    # Parsing: use xml.etree.ElementTree or lxml
    logger.info("OFAC pipeline stub — implement XML parsing and Fabric write")
