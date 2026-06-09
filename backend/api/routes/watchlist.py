from fastapi import APIRouter, HTTPException
from shared.schemas import WatchlistEntry, WatchlistAddRequest, EntityFingerprint
from shared.logger import get_logger
from fabric.client import get_fabric_client
import uuid
from datetime import datetime
from agents.resurface.scheduler import start_watchlist_polling, get_scheduler

router = APIRouter(prefix="/watchlist", tags=["watchlist"])
logger = get_logger(__name__)

WATCHLIST_TABLE = "shadow_intel_watchlist"

@router.post("", response_model=dict)
async def add_to_watchlist(request: WatchlistAddRequest):
    client = get_fabric_client()
    
    # Read existing
    watchlist = await client.read_lakehouse_table(WATCHLIST_TABLE)
    
    # Check if exists
    for entity in watchlist:
        if entity.get("canonical_name", "").lower() == request.canonical_name.lower():
            return {"message": "Already on watchlist", "entity_id": entity["entity_id"]}
            
    # Add new
    entity_id = str(uuid.uuid4())
    new_entry = {
        "entity_id": entity_id,
        "canonical_name": request.canonical_name,
        "aliases": request.aliases or [],
        "jurisdictions": request.jurisdictions or [],
        "directors": request.directors or [],
        "addresses": request.addresses or [],
        "registration_numbers": request.registration_numbers or [],
        "sanctions_lists": request.sanctions_lists or [],
        "confidence_threshold": request.confidence_threshold,
        "added_at": datetime.utcnow().isoformat(),
        "last_checked": None,
        "last_alert": None
    }
    
    watchlist.append(new_entry)
    success = await client.write_to_lakehouse(WATCHLIST_TABLE, watchlist)
    
    if success:
        fingerprint = EntityFingerprint(
            entity_id=entity_id,
            canonical_name=request.canonical_name,
            aliases=request.aliases or [],
            jurisdictions=request.jurisdictions or [],
            directors=request.directors or []
        )
        
        # Ensure scheduler is running
        scheduler = get_scheduler()
        if not scheduler or not scheduler.running:
            await start_watchlist_polling(interval_minutes=30)
            
        # FOR TESTING: Run the engine immediately so you can see the alert without waiting 30 minutes
        from agents.resurface.agent import ResurfaceAlertEngine
        import asyncio
        asyncio.create_task(ResurfaceAlertEngine().run(fingerprint, request.confidence_threshold))
            
        return {"message": "Added to watchlist", "entity_id": entity_id}
        
    raise HTTPException(status_code=500, detail="Failed to write to Fabric Lakehouse")

@router.get("", response_model=list[WatchlistEntry])
async def list_watchlist():
    client = get_fabric_client()
    watchlist = await client.read_lakehouse_table(WATCHLIST_TABLE)
    return watchlist

@router.delete("/{entity_id}")
async def remove_from_watchlist(entity_id: str):
    client = get_fabric_client()
    watchlist = await client.read_lakehouse_table(WATCHLIST_TABLE)
    
    original_len = len(watchlist)
    watchlist = [e for e in watchlist if e.get("entity_id") != entity_id]
    
    if len(watchlist) == original_len:
        raise HTTPException(status_code=404, detail="Not found")
        
    success = await client.write_to_lakehouse(WATCHLIST_TABLE, watchlist)
    if success:
        return {"message": "Removed"}
    raise HTTPException(status_code=500, detail="Failed to write to Fabric Lakehouse")
