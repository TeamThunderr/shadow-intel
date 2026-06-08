from typing import List, Optional
from datetime import datetime
from fabric.client import get_fabric_client
from shared.schemas import WatchlistEntry, AlertPayload
from shared.logger import get_logger

logger = get_logger(__name__)

WATCHLIST_TABLE = "watchlist"
ALERTS_TABLE = "alerts"


class WatchlistStore:
    def __init__(self):
        self.client = get_fabric_client()

    async def add_entity(self, entry: WatchlistEntry) -> bool:
        logger.info(f"Adding entity {entry.entity_id} to Watchlist.")
        current_entries = await self.list_entities()
        # Remove if already exists to overwrite
        current_entries = [e for e in current_entries if e.entity_id != entry.entity_id]
        current_entries.append(entry)
        
        rows = [e.model_dump(mode="json") for e in current_entries]
        return await self.client.write_to_lakehouse(WATCHLIST_TABLE, rows)

    async def remove_entity(self, entity_id: str) -> bool:
        logger.info(f"Removing entity {entity_id} from Watchlist.")
        current_entries = await self.list_entities()
        new_entries = [e for e in current_entries if e.entity_id != entity_id]
        
        rows = [e.model_dump(mode="json") for e in new_entries]
        return await self.client.write_to_lakehouse(WATCHLIST_TABLE, rows)

    async def list_entities(self) -> List[WatchlistEntry]:
        rows = await self.client.read_lakehouse_table(WATCHLIST_TABLE)
        entries = []
        for row in rows:
            try:
                entries.append(WatchlistEntry(**row))
            except Exception as e:
                logger.error(f"Failed to parse watchlist entry: {e}")
        return entries

    async def get_entity(self, entity_id: str) -> Optional[WatchlistEntry]:
        entries = await self.list_entities()
        for e in entries:
            if e.entity_id == entity_id:
                return e
        return None

    async def update_last_checked(self, entity_id: str) -> bool:
        entries = await self.list_entities()
        updated = False
        for e in entries:
            if e.entity_id == entity_id:
                e.last_checked = datetime.utcnow()
                updated = True
                break
        
        if updated:
            rows = [e.model_dump(mode="json") for e in entries]
            return await self.client.write_to_lakehouse(WATCHLIST_TABLE, rows)
        return False

    async def update_last_alert(self, entity_id: str) -> bool:
        entries = await self.list_entities()
        updated = False
        for e in entries:
            if e.entity_id == entity_id:
                e.last_alert = datetime.utcnow()
                updated = True
                break
        
        if updated:
            rows = [e.model_dump(mode="json") for e in entries]
            return await self.client.write_to_lakehouse(WATCHLIST_TABLE, rows)
        return False


class AlertStore:
    def __init__(self):
        self.client = get_fabric_client()

    async def write_alert(self, alert: AlertPayload) -> bool:
        logger.info(f"Writing alert {alert.alert_id} for entity {alert.entity_id}")
        current_alerts = await self.get_alert_history()
        current_alerts.append(alert)
        
        rows = [a.model_dump(mode="json") for a in current_alerts]
        return await self.client.write_to_lakehouse(ALERTS_TABLE, rows)

    async def get_alert_history(self) -> List[AlertPayload]:
        rows = await self.client.read_lakehouse_table(ALERTS_TABLE)
        alerts = []
        for row in rows:
            try:
                alerts.append(AlertPayload(**row))
            except Exception as e:
                logger.error(f"Failed to parse alert payload: {e}")
        return alerts
