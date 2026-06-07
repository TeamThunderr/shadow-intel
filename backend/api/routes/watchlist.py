from fastapi import APIRouter, HTTPException
from shared.schemas import WatchlistEntry, WatchlistAddRequest
from shared.logger import get_logger

router = APIRouter(prefix="/watchlist", tags=["watchlist"])
logger = get_logger(__name__)

# In-memory watchlist (P4: connect to Fabric for persistence)
watchlist: dict[str, WatchlistEntry] = {}


@router.post("", response_model=dict)
async def add_to_watchlist(request: WatchlistAddRequest):
    # TODO (P4): Store fingerprint in Fabric, start scheduler polling
    return {"message": "Added to watchlist", "entity_id": "stub"}


@router.get("", response_model=list[WatchlistEntry])
async def list_watchlist():
    return list(watchlist.values())


@router.delete("/{entity_id}")
async def remove_from_watchlist(entity_id: str):
    if entity_id not in watchlist:
        raise HTTPException(status_code=404, detail="Not found")
    del watchlist[entity_id]
    return {"message": "Removed"}
