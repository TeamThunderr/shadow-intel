"""
UN Security Council Consolidated Sanctions List.
Source: https://scsanctions.un.org/resources/xml/en/consolidated.xml
Free, no API key required.
"""

import xml.etree.ElementTree as ET
import httpx
from datetime import datetime, timedelta
from rapidfuzz import fuzz
from shared.logger import get_logger

logger = get_logger(__name__)

_cache: dict = {"entries": [], "last_fetched": None}

UN_XML_URL = "https://scsanctions.un.org/resources/xml/en/consolidated.xml"
CACHE_TTL_HOURS = 24
FUZZY_THRESHOLD = 80


async def _fetch_un_list() -> list[dict]:
    logger.info("Downloading UN Consolidated Sanctions list...")
    async with httpx.AsyncClient(timeout=30.0) as client:
        resp = await client.get(UN_XML_URL)
        resp.raise_for_status()
        raw_xml = resp.text

    root = ET.fromstring(raw_xml)
    entries = []

    # UN XML structure: INDIVIDUALS and ENTITIES sections
    for individual in root.findall(".//INDIVIDUAL"):
        first = individual.findtext("FIRST_NAME", default="").strip()
        second = individual.findtext("SECOND_NAME", default="").strip()
        third = individual.findtext("THIRD_NAME", default="").strip()
        fourth = individual.findtext("FOURTH_NAME", default="").strip()
        full_name = " ".join(filter(None, [first, second, third, fourth]))
        un_id = individual.findtext("DATAID", default="")

        aliases = []
        for alias in individual.findall(".//ALIAS"):
            a_quality = alias.findtext("QUALITY", default="")
            a_name = alias.findtext("ALIAS_NAME", default="").strip()
            if a_name:
                aliases.append({"name": a_name, "quality": a_quality})

        if full_name:
            entries.append({
                "id": un_id,
                "name": full_name,
                "type": "individual",
                "aliases": [a["name"] for a in aliases],
                "all_names": [full_name] + [a["name"] for a in aliases],
                "list_type": "UN Consolidated",
            })

    for entity in root.findall(".//ENTITY"):
        name = entity.findtext("FIRST_NAME", default="").strip()
        un_id = entity.findtext("DATAID", default="")
        aliases = []
        for alias in entity.findall(".//ALIAS"):
            a_name = alias.findtext("ALIAS_NAME", default="").strip()
            if a_name:
                aliases.append(a_name)

        if name:
            entries.append({
                "id": un_id,
                "name": name,
                "type": "entity",
                "aliases": aliases,
                "all_names": [name] + aliases,
                "list_type": "UN Consolidated",
            })

    logger.info(f"UN Sanctions: loaded {len(entries)} entries")
    return entries


async def _ensure_cache():
    now = datetime.utcnow()
    last = _cache["last_fetched"]
    if not last or (now - last) > timedelta(hours=CACHE_TTL_HOURS):
        try:
            _cache["entries"] = await _fetch_un_list()
            _cache["last_fetched"] = now
        except Exception as e:
            logger.error(f"Failed to refresh UN cache: {e}")


async def query_un_sanctions(name: str) -> list[dict]:
    """Search UN Consolidated Sanctions list for fuzzy name matches."""
    await _ensure_cache()
    entries = _cache["entries"]
    if not entries:
        return []

    results = []
    name_upper = name.upper()

    for entry in entries:
        best_score = 0
        best_matched = ""
        for candidate in entry["all_names"]:
            score = fuzz.token_sort_ratio(name_upper, candidate.upper())
            if score > best_score:
                best_score = score
                best_matched = candidate

        if best_score >= FUZZY_THRESHOLD:
            results.append({
                "id": entry["id"],
                "name": entry["name"],
                "matched_name": best_matched,
                "type": entry["type"],
                "aliases": entry["aliases"],
                "list_type": "UN Consolidated",
                "confidence": round(best_score / 100, 3),
                "source": "UN Security Council",
            })

    results.sort(key=lambda x: x["confidence"], reverse=True)
    logger.info(f"UN Sanctions: {len(results)} matches for '{name}'")
    return results[:10]
