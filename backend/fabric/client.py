from azure.identity import ClientSecretCredential
from shared.config import get_settings
from shared.logger import get_logger

logger = get_logger(__name__)

FABRIC_API_BASE = "https://api.fabric.microsoft.com/v1"


class FabricClient:
    """
    Microsoft Fabric IQ — client for reading/writing data in Fabric Lakehouse.
    Uses Azure AD ClientSecretCredential for authentication.
    """

    def __init__(self):
        settings = get_settings()
        self._settings = settings
        self._credential = ClientSecretCredential(
            tenant_id=settings.fabric_tenant_id,
            client_id=settings.fabric_client_id,
            client_secret=settings.fabric_client_secret,
        )
        self._token: str | None = None

    def _get_token(self) -> str:
        """Get a fresh Azure AD token for Fabric API calls."""
        token = self._credential.get_token("https://analysis.windows.net/powerbi/api/.default")
        return token.token

    async def read_lakehouse_table(self, table_name: str, query: str = "") -> list[dict]:
        """
        Read data from a Fabric Lakehouse delta table.
        Optionally filter with a SQL-style WHERE clause.
        """
        # TODO: implement Fabric Lakehouse REST API call
        logger.info(f"Reading Fabric table: {table_name}")
        return []

    async def write_to_lakehouse(self, table_name: str, rows: list[dict]) -> bool:
        """
        Write rows to a Fabric Lakehouse delta table.
        Used by pipelines to ingest external data.
        """
        # TODO: implement Fabric write API
        logger.info(f"Writing {len(rows)} rows to Fabric table: {table_name}")
        return True


# Singleton instance
_client: FabricClient | None = None


def get_fabric_client() -> FabricClient:
    global _client
    if _client is None:
        _client = FabricClient()
    return _client
