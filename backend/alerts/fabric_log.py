from shared.schemas import AlertPayload
from fabric.client import get_fabric_client
from shared.logger import get_logger
from datetime import datetime
import uuid

logger = get_logger(__name__)

FABRIC_ALERTS_TABLE = "shadow_intel_alerts"

async def write_alert_log(alert: AlertPayload, routing: dict, delivery_status: str) -> str:
    """Record a generated alert and its routing decision into Fabric."""
    client = get_fabric_client()
    
    alert_id = str(uuid.uuid4())
    timestamp = alert.timestamp.isoformat() if hasattr(alert, "timestamp") and alert.timestamp else datetime.utcnow().isoformat()
    
    delivery_methods = []
    if routing.get("send_teams"):
        delivery_methods.append("teams")
    if routing.get("send_email"):
        delivery_methods.append("email")
    if routing.get("log_only"):
        delivery_methods.append("log")
        
    row = {
        "alert_id": alert_id,
        "entity_id": alert.entity_id,
        "entity_name": alert.entity_name,
        "confidence": alert.confidence,
        "risk_level": alert.risk_level.value,
        "delivery_method": ",".join(delivery_methods),
        "status": delivery_status,
        "timestamp": timestamp
    }
    
    try:
        # Note: in a real big data scenario, we'd append, not read-modify-write.
        # But our FabricClient mock handles simple overwrites for the prototype.
        existing = await client.read_lakehouse_table(FABRIC_ALERTS_TABLE)
        existing.append(row)
        success = await client.write_to_lakehouse(FABRIC_ALERTS_TABLE, existing)
        
        if success:
            logger.info(f"Wrote alert log {alert_id} to Fabric.")
        else:
            logger.warning(f"Failed to write alert log {alert_id} to Fabric.")
    except Exception as e:
        logger.error(f"Error writing alert log to Fabric: {e}")
        
    return alert_id

async def update_alert_status(alert_id: str, new_status: str) -> bool:
    """Update the status of an existing alert in Fabric."""
    client = get_fabric_client()
    try:
        existing = await client.read_lakehouse_table(FABRIC_ALERTS_TABLE)
        updated = False
        for row in existing:
            if row.get("alert_id") == alert_id:
                row["status"] = new_status
                updated = True
                break
        
        if updated:
            return await client.write_to_lakehouse(FABRIC_ALERTS_TABLE, existing)
        return False
    except Exception as e:
        logger.error(f"Error updating alert status in Fabric: {e}")
        return False

async def get_alert_history(entity_id: str = None) -> list[dict]:
    """Retrieve alert history from Fabric."""
    client = get_fabric_client()
    try:
        existing = await client.read_lakehouse_table(FABRIC_ALERTS_TABLE)
        if entity_id:
            return [r for r in existing if r.get("entity_id") == entity_id]
        return existing
    except Exception as e:
        logger.error(f"Error fetching alert history from Fabric: {e}")
        return []
