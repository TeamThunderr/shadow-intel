"""
OpenOwnership API Integration

Queries the OpenOwnership Register for beneficial ownership data.
Supports company search and beneficial owner lookup.

API: https://register.openownership.org/api
Documentation: https://docs.openownership.org/register/
"""

from typing import Optional, List, Dict, Any
from datetime import datetime
import asyncio
from shared.http_client import get_json
from shared.logger import get_logger

logger = get_logger(__name__)

OPENOWNERSHIP_BASE = "https://register.openownership.org/api"
REQUEST_TIMEOUT = 10
MAX_RETRIES = 2
RETRY_DELAY = 1


async def search_companies(
    entity_name: str,
    jurisdiction: Optional[str] = None,
    limit: int = 10
) -> List[Dict[str, Any]]:
    """
    Search for companies in OpenOwnership Register.
    
    Args:
        entity_name: Company name to search for
        jurisdiction: Optional jurisdiction code filter (e.g., 'gb', 'us')
        limit: Maximum results to return
        
    Returns:
        List of company records with basic info
    """
    try:
        logger.info(f"Searching OpenOwnership for companies: {entity_name}")
        
        # Search endpoint
        url = f"{OPENOWNERSHIP_BASE}/releases"
        params = {
            "filter[compilation__schema]": "bods",
            "filter[data__entities__name]": entity_name,
            "page[size]": min(limit, 100),
        }
        
        if jurisdiction:
            params["filter[data__entities__country_of_residence__code]"] = jurisdiction
        
        data = await _request_with_retry(url, params)
        
        if not data or "data" not in data:
            logger.warning(f"No results found for {entity_name}")
            return []
        
        # Parse and normalize results
        results = []
        for release in data.get("data", []):
            for entity in release.get("entities", []):
                if entity.get("type") == "Entity":
                    results.append({
                        "id": entity.get("id"),
                        "name": entity.get("name"),
                        "type": entity.get("entity_type"),
                        "country": entity.get("country_of_residence", {}).get("code"),
                        "source": "openownership",
                        "source_url": f"{OPENOWNERSHIP_BASE}/releases/{release.get('id')}",
                    })
        
        logger.info(f"Found {len(results)} companies in OpenOwnership")
        return results[:limit]
        
    except Exception as e:
        logger.error(f"Error searching OpenOwnership: {e}")
        return []


async def get_beneficial_owners(
    entity_id: str
) -> List[Dict[str, Any]]:
    """
    Get beneficial owners for an entity in OpenOwnership Register.
    
    Args:
        entity_id: OpenOwnership entity ID
        
    Returns:
        List of beneficial owner records
    """
    try:
        logger.info(f"Fetching beneficial owners for entity: {entity_id}")
        
        url = f"{OPENOWNERSHIP_BASE}/entities/{entity_id}"
        data = await _request_with_retry(url)
        
        if not data:
            return []
        
        owners = []
        
        # Parse relationships (interests, control, ownership)
        for relationship in data.get("relationships", []):
            if relationship.get("type") == "Interest":
                owner = {
                    "id": relationship.get("interestee_id"),
                    "name": relationship.get("interestee_name"),
                    "type": relationship.get("interestee_type"),  # person, entity, unknown
                    "ownership_percentage": relationship.get("percentage"),
                    "share_type": relationship.get("share_type"),  # shares, ownership, control
                    "start_date": relationship.get("start_date"),
                    "end_date": relationship.get("end_date"),
                    "source": "openownership",
                }
                owners.append(owner)
        
        logger.info(f"Found {len(owners)} beneficial owners")
        return owners
        
    except Exception as e:
        logger.error(f"Error fetching beneficial owners: {e}")
        return []


async def get_ownership_chain(
    entity_id: str,
    max_depth: int = 5
) -> List[List[Dict[str, Any]]]:
    """
    Get complete ownership chain (paths from entity to UBOs).
    
    Args:
        entity_id: Starting entity ID
        max_depth: Maximum chain depth to traverse
        
    Returns:
        List of ownership paths (each path is a list of entities)
    """
    try:
        logger.info(f"Tracing ownership chain for entity: {entity_id}")
        
        visited = set()
        paths = []
        
        async def trace_chain(
            current_id: str,
            path: List[Dict[str, Any]],
            depth: int
        ) -> None:
            """Recursively trace ownership chain."""
            if depth >= max_depth or current_id in visited:
                if path:
                    paths.append(path)
                return
            
            visited.add(current_id)
            
            # Get owners of current entity
            owners = await get_beneficial_owners(current_id)
            
            if not owners:
                # Leaf node - natural person or dead end
                if path:
                    paths.append(path)
            else:
                # Continue tracing
                for owner in owners:
                    new_path = path + [owner]
                    await trace_chain(owner.get("id", ""), new_path, depth + 1)
        
        # Start tracing
        initial = await _get_entity(entity_id)
        if initial:
            await trace_chain(entity_id, [initial], 0)
        
        logger.info(f"Traced {len(paths)} ownership paths")
        return paths
        
    except Exception as e:
        logger.error(f"Error tracing ownership chain: {e}")
        return []


async def _get_entity(entity_id: str) -> Optional[Dict[str, Any]]:
    """Get entity details."""
    try:
        url = f"{OPENOWNERSHIP_BASE}/entities/{entity_id}"
        data = await _request_with_retry(url)
        
        if data:
            return {
                "id": data.get("id"),
                "name": data.get("name"),
                "type": data.get("entity_type"),
                "country": data.get("country_of_residence", {}).get("code"),
            }
    except Exception as e:
        logger.debug(f"Error fetching entity {entity_id}: {e}")
    
    return None


async def _request_with_retry(
    url: str,
    params: Optional[Dict[str, str]] = None,
    headers: Optional[Dict[str, str]] = None
) -> Optional[Dict[str, Any]]:
    """
    Make HTTP request with retry logic and timeout.
    
    Args:
        url: Request URL
        params: Query parameters
        headers: HTTP headers
        
    Returns:
        Response data or None on failure
    """
    for attempt in range(MAX_RETRIES):
        try:
            result = await get_json(
                url,
                params=params,
                headers=headers,
                timeout=REQUEST_TIMEOUT
            )
            return result
        except asyncio.TimeoutError:
            if attempt < MAX_RETRIES - 1:
                logger.warning(f"Timeout on {url}, retrying...")
                await asyncio.sleep(RETRY_DELAY)
            else:
                logger.error(f"Timeout after {MAX_RETRIES} attempts: {url}")
        except Exception as e:
            if attempt < MAX_RETRIES - 1:
                logger.debug(f"Retry attempt {attempt + 1} for {url}: {e}")
                await asyncio.sleep(RETRY_DELAY)
            else:
                logger.error(f"Error fetching {url}: {e}")
    
    return None
