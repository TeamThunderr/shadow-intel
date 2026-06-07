from fabric.client import get_fabric_client
from shared.logger import get_logger

logger = get_logger(__name__)

ICIJ_OFFSHORE_LEAKS_URL = "https://offshoreleaks-data.icij.org/offshoreleaks/csv/full-oldb.LATEST.zip"


async def ingest_icij_offshore_leaks():
    """
    Download ICIJ Offshore Leaks database and store in Fabric Lakehouse.
    Covers: Panama Papers, Pandora Papers, Offshore Leaks, Bahamas Leaks.
    """
    logger.info("Starting ICIJ ingestion pipeline")
    client = get_fabric_client()

    # TODO: download ZIP, extract CSVs, parse entities/relationships, write to Fabric
    logger.info("ICIJ pipeline stub — implement ZIP extraction and Fabric write")
