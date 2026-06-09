import os
import asyncio
import httpx
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
        self._credential = None

    def _get_token(self) -> str:
        """Get a fresh Azure AD token for Fabric API calls."""
        if not self._credential:
            # Prevent crashes if placeholders are still in the .env file
            if not self._settings.fabric_tenant_id or "your_" in self._settings.fabric_tenant_id:
                logger.error("Fabric API keys are missing or invalid placeholders in .env file. Cannot connect to Fabric.")
                return ""
                
            self._credential = ClientSecretCredential(
                tenant_id=self._settings.fabric_tenant_id,
                client_id=self._settings.fabric_client_id,
                client_secret=self._settings.fabric_client_secret,
            )
            
        token = self._credential.get_token("https://api.fabric.microsoft.com/.default")
        return token.token

    async def read_lakehouse_table(self, table_name: str, query: str = "") -> list[dict]:
        """
        Read data from a Fabric Lakehouse delta table.
        """
        logger.info(f"Reading Fabric table: {table_name}")
        token = self._get_token()
        if not token:
            return []
            
        url = f"{FABRIC_API_BASE}/workspaces/{self._settings.fabric_workspace_id}/lakehouses/{self._settings.fabric_lakehouse_id}/tables/{table_name}/data"
        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json"
        }
        
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(url, headers=headers)
                response.raise_for_status()
                return response.json().get("data", [])
        except Exception as e:
            logger.error(f"Failed to read from Fabric Lakehouse: {e}")
            return []

    async def write_to_lakehouse(self, table_name: str, rows: list[dict]) -> bool:
        """
        Write rows to a Fabric Lakehouse delta table.
        """
        logger.info(f"Writing {len(rows)} rows to Fabric table: {table_name}")
        token = self._get_token()
        if not token:
            return False
            
        url = f"{FABRIC_API_BASE}/workspaces/{self._settings.fabric_workspace_id}/lakehouses/{self._settings.fabric_lakehouse_id}/tables/{table_name}/data"
        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json"
        }
        
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(url, headers=headers, json={"data": rows})
                response.raise_for_status()
                return True
        except Exception as e:
            logger.error(f"Failed to write to Fabric Lakehouse: {e}")
            return False


# Singleton instance
_client: FabricClient | None = None


def get_fabric_client() -> FabricClient:
    global _client
    if _client is None:
        _client = FabricClient()
    return _client
