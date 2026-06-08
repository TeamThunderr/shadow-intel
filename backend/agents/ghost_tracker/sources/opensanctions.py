"""
OpenSanctions API integration.
Aggregates 100+ sanctions and watchlists globally.
Get free API key at: https://www.opensanctions.org/api/
Docs: https://api.opensanctions.org/
"""

import httpx
from rapidfuzz import fuzz
from shared.logger import get_logger

logger = get_logger(__name__)

OPENSANCTIONS_BASE = "https://api.opensanctions.org"
FUZZY_THRESHOLD = 0.75  # 0.0-1.0 scale


async def query_opensanctions(name: str, settings) -> list[dict]:
    """
    Use OpenSanctions /match endpoint for entity matching.
    Falls back to /search if match endpoint fails.
    """
    if not settings.opensanctions_api_key:
        logger.warning("No OpenSanctions API key — trying public endpoint")

    headers = {}
    if settings.opensanctions_api_key:
        headers["Authorization"] = f"ApiKey {settings.opensanctions_api_key}"

    results = await _match_entity(name, headers)
    if not results:
        results = await _search_entity(name, headers)

    return results


async def _match_entity(name: str, headers: dict) -> list[dict]:
    """
    POST /match — structured entity matching (more accurate).
    Returns scored matches from the default dataset.
    """
    url = f"{OPENSANCTIONS_BASE}/match/default"
    payload = {
        "queries": {
            "q1": {
                "schema": "Thing",
                "properties": {"name": [name]}
            }
        }
    }

    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.post(url, json=payload, headers=headers)
            resp.raise_for_status()
            data = resp.json()
    except httpx.HTTPStatusError as e:
        logger.warning(f"OpenSanctions /match returned {e.response.status_code}")
        return []
    except Exception as e:
        logger.error(f"OpenSanctions /match error: {e}")
        return []

    results = []
    responses = data.get("responses", {})
    q1_results = responses.get("q1", {}).get("results", [])

    for match in q1_results:
        score = match.get("score", 0.0)
        if score < FUZZY_THRESHOLD:
            continue

        props = match.get("properties", {})
        names = props.get("name", [])
        aliases = props.get("alias", [])
        countries = props.get("country", [])
        sanctions = props.get("topics", [])

        results.append({
            "id": match.get("id"),
            "name": names[0] if names else name,
            "aliases": aliases,
            "countries": countries,
            "sanctions_topics": sanctions,
            "datasets": match.get("datasets", []),
            "score": score,
            "confidence": round(score, 3),
            "source": "OpenSanctions",
            "url": f"https://www.opensanctions.org/entities/{match.get('id')}/",
        })

    logger.info(f"OpenSanctions /match: {len(results)} results for '{name}'")
    return results


async def _search_entity(name: str, headers: dict) -> list[dict]:
    """
    GET /search — text search fallback.
    Less structured but works without an API key (rate limited).
    """
    url = f"{OPENSANCTIONS_BASE}/search/default"
    params = {"q": name, "limit": 10, "schema": "Thing"}

    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.get(url, params=params, headers=headers)
            resp.raise_for_status()
            data = resp.json()
    except Exception as e:
        logger.error(f"OpenSanctions /search error: {e}")
        return []

    results = []
    for result in data.get("results", []):
        props = result.get("properties", {})
        names = props.get("name", [])
        candidate_name = names[0] if names else ""
        similarity = fuzz.token_sort_ratio(name.upper(), candidate_name.upper()) / 100

        if similarity < FUZZY_THRESHOLD:
            continue

        results.append({
            "id": result.get("id"),
            "name": candidate_name,
            "aliases": props.get("alias", []),
            "countries": props.get("country", []),
            "sanctions_topics": props.get("topics", []),
            "datasets": result.get("datasets", []),
            "score": similarity,
            "confidence": round(similarity, 3),
            "source": "OpenSanctions",
            "url": f"https://www.opensanctions.org/entities/{result.get('id')}/",
        })

    logger.info(f"OpenSanctions /search: {len(results)} results for '{name}'")
    return results
