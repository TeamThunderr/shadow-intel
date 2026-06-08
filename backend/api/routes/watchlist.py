from fastapi import APIRouter, HTTPException
from shared.schemas import WatchlistEntry, WatchlistAddRequest, EntityFingerprint
from shared.logger import get_logger
from agents.resurface.store import WatchlistStore
import uuid
from datetime import datetime
from agents.resurface.scheduler import start_watchlist_polling, get_scheduler

router = APIRouter(prefix="/watchlist", tags=["watchlist"])
logger = get_logger(__name__)


@router.post("", response_model=dict)
async def add_to_watchlist(request: WatchlistAddRequest):
    entity_id = str(uuid.uuid4())
    
    # Create an initial fingerprint
    fingerprint = EntityFingerprint(
        entity_id=entity_id,
        canonical_name=request.name,
        aliases=[],
        jurisdictions=[],
        directors=[]
    )
    
    entry = WatchlistEntry(
        entity_id=entity_id,
        entity_name=request.name,
        fingerprint=fingerprint,
        confidence_threshold=request.confidence_threshold,
        added_at=datetime.utcnow()
    )
    
    store = WatchlistStore()
    success = await store.add_entity(entry)
    
    if success:
        # Ensure scheduler is running
        scheduler = get_scheduler()
        if not scheduler or not scheduler.running:
            await start_watchlist_polling(interval_minutes=30)
            
        # FOR TESTING: Run the engine immediately so you can see the alert without waiting 30 minutes
        from agents.resurface.agent import ResurfaceAlertEngine
        import asyncio
        asyncio.create_task(ResurfaceAlertEngine().run(fingerprint, request.confidence_threshold))
            
        return {"message": "Added to watchlist", "entity_id": entity_id}
    else:
        raise HTTPException(status_code=500, detail="Failed to save to Watchlist storage.")


@router.get("", response_model=list[WatchlistEntry])
async def list_watchlist():
    store = WatchlistStore()
    return await store.list_entities()


@router.delete("/{entity_id}")
async def remove_from_watchlist(entity_id: str):
    store = WatchlistStore()
    
    # Check if exists first
    entry = await store.get_entity(entity_id)
    if not entry:
        raise HTTPException(status_code=404, detail="Not found")
        
    success = await store.remove_entity(entity_id)
    if success:
        return {"message": "Removed"}
    else:
        raise HTTPException(status_code=500, detail="Failed to remove from Watchlist storage.")
