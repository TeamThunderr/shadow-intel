import asyncio
import httpx
from shared.http_client import get_client
from shared.logger import get_logger
from shared.config import get_settings
from rapidfuzz import fuzz
from fabric.pipeline import normalize_entity_name

logger = get_logger(__name__)

OCCRP_BASE = "https://aleph.occrp.org/api/2"

# Global rate limiting semaphore for external APIs
api_semaphore = asyncio.Semaphore(5)


async def search_occrp(name: str) -> list[dict]:
    """
    Query OCCRP Aleph investigative database for entity mentions.
    Aleph contains leaked documents, court records, and corporate registries.
    """
    settings = get_settings()
    if not settings.occrp_api_key:
        logger.warning("No OCCRP API key — skipping")
        return []

    url = f"{OCCRP_BASE}/search"
    params = {"q": name, "limit": 20}
    headers = {"Authorization": f"ApiKey {settings.occrp_api_key}"}

    logger.info(f"Querying OCCRP Aleph for: {name}")
    
    async with api_semaphore:
        try:
            client = await get_client()
            resp = await client.get(url, params=params, headers=headers, timeout=10.0)
            
            if resp.status_code == 401:
                logger.error("OCCRP search failed: 401 Unauthorized — check API key")
                return []
            elif resp.status_code == 403:
                logger.error("OCCRP search failed: 403 Forbidden")
                return []
            elif resp.status_code == 404:
                logger.error("OCCRP search failed: 404 Not Found")
                return []
            elif resp.status_code == 429:
                logger.warning("OCCRP search rate limited: 429 Too Many Requests")
                return []
                
            resp.raise_for_status()
            data = resp.json()
        except httpx.HTTPStatusError as e:
            logger.error(f"OCCRP HTTP status error: {e.response.status_code} for query '{name}'")
            return []
        except httpx.TimeoutException:
            logger.error(f"OCCRP connection timed out for query '{name}'")
            return []
        except Exception as e:
            logger.error(f"OCCRP request failed for query '{name}': {e}")
            return []

    results = data.get("results", [])
    signals = []
    
    q_norm = normalize_entity_name(name)
    
    for res in results:
        try:
            entity_name = res.get("caption") or (res.get("properties", {}).get("name", [""])[0]) or name
            collection = res.get("collection", {}).get("label") or "OCCRP Collection"
            schema_name = res.get("schema", "Thing")
            countries = res.get("properties", {}).get("country", []) or res.get("countries", [])
            country = countries[0] if countries else "unknown"
            url_val = res.get("links", {}).get("ui") or f"https://aleph.occrp.org/entities/{res.get('id')}"
            
            # Extract description / notes as snippet
            snippet = ""
            desc = res.get("properties", {}).get("description", [])
            notes = res.get("properties", {}).get("notes", [])
            if desc:
                snippet = desc[0]
            elif notes:
                snippet = notes[0]
            else:
                snippet = f"Entity '{entity_name}' found in OCCRP Aleph database under schema {schema_name}."
                
            e_norm = normalize_entity_name(entity_name)
            confidence = fuzz.token_sort_ratio(q_norm, e_norm) / 100.0 if q_norm and e_norm else 0.5
            
            signals.append({
                "source": "OCCRP",
                "title": f"OCCRP Search: {entity_name} ({schema_name})",
                "url": url_val,
                "entity": entity_name,
                "country": country,
                "summary": f"Source: {collection}. Schema: {schema_name}. Details: {snippet}",
                "confidence": confidence,
                "published_date": None
            })
        except Exception as pe:
            logger.warning(f"Error parsing OCCRP result item: {pe}")
            
    logger.info(f"OCCRP returned {len(signals)} parsed signals for: {name}")
    return signals
