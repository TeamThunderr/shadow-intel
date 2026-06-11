"""
OFAC SDN (Specially Designated Nationals) list integration.
Source: https://www.treasury.gov/ofac/downloads/sdn.xml
Free, no API key required. Refreshed daily by OFAC.
"""

import xml.etree.ElementTree as ET
from datetime import datetime, timedelta
from rapidfuzz import fuzz
from shared.logger import get_logger
import httpx

logger = get_logger(__name__)

# In-memory cache
_cache: dict = {
    "entries": [],
    "last_fetched": None,
}

OFAC_XML_URL = "https://www.treasury.gov/ofac/downloads/sdn.xml"
CACHE_TTL_HOURS = 24
FUZZY_THRESHOLD = 80  # 0-100 scale (rapidfuzz)


async def _fetch_and_parse_ofac() -> list[dict]:
    """Download and parse OFAC SDN XML list into a flat list of entries."""
    logger.info("Downloading OFAC SDN list...")
    async with httpx.AsyncClient(timeout=30.0) as client:
        resp = await client.get(OFAC_XML_URL)
        resp.raise_for_status()
        raw_xml = resp.text

    root = ET.fromstring(raw_xml)
    ns = {"ofac": "https://tempuri.org/sdnList.xsd"}
    entries = []

    for entry in root.findall(".//ofac:sdnEntry", ns):
        # Extract name parts
        last = entry.findtext("ofac:lastName", default="", namespaces=ns).strip()
        first = entry.findtext("ofac:firstName", default="", namespaces=ns).strip()
        full_name = f"{first} {last}".strip() if first else last
        uid = entry.findtext("ofac:uid", default="", namespaces=ns)
        sdn_type = entry.findtext("ofac:sdnType", default="", namespaces=ns)

        # Extract AKAs (aliases)
        aliases = []
        for aka in entry.findall(".//ofac:aka", ns):
            aka_last = aka.findtext("ofac:lastName", default="", namespaces=ns).strip()
            aka_first = aka.findtext("ofac:firstName", default="", namespaces=ns).strip()
            alias = f"{aka_first} {aka_last}".strip() if aka_first else aka_last
            if alias:
                aliases.append(alias)

        # Extract programs (sanction programs e.g. IRAN, RUSSIA)
        programs = [
            p.text.strip()
            for p in entry.findall(".//ofac:program", ns)
            if p.text
        ]

        if full_name:
            entries.append({
                "uid": uid,
                "name": full_name,
                "aliases": aliases,
                "type": sdn_type,
                "programs": programs,
                "all_names": [full_name] + aliases,
            })

    logger.info(f"OFAC: loaded {len(entries)} entries")
    return entries


async def _ensure_cache():
    """Refresh cache if stale or empty."""
    now = datetime.utcnow()
    last = _cache["last_fetched"]
    if not last or (now - last) > timedelta(hours=CACHE_TTL_HOURS):
        try:
            _cache["entries"] = await _fetch_and_parse_ofac()
            _cache["last_fetched"] = now
        except Exception as e:
            logger.error(f"Failed to refresh OFAC cache: {e}")
            if not _cache["entries"]:
                return  # no fallback available


async def query_ofac(name: str) -> list[dict]:
    """
    Search the OFAC SDN list for fuzzy name matches.

    Fast-path: tries the local parquet snapshot first (instant, no network).
    Falls back to downloading the OFAC XML only when the parquet returns nothing.
    """
    # ── Fast-path: local parquet ───────────────────────────────────────────────
    try:
        from shared.data_loader import search_ofac as _local_search
        local_hits = _local_search(name, threshold=FUZZY_THRESHOLD / 100.0)
        if local_hits:
            logger.info(f"OFAC (local parquet): {len(local_hits)} matches for '{name}'")
            return [
                {
                    "uid":          h["data"].get("uid", ""),
                    "name":         h["name"],
                    "matched_name": h["name"],
                    "aliases":      [],
                    "type":         h["data"].get("sdn_type", h["data"].get("sdnType", "")),
                    "programs":     [],
                    "confidence":   h["confidence"],
                    "source":       "OFAC SDN",
                }
                for h in local_hits
            ]
    except Exception as exc:
        logger.warning(f"OFAC local fast-path failed, falling back to XML: {exc}")

    # ── Fallback: download OFAC XML ───────────────────────────────────────────
    await _ensure_cache()
    entries = _cache["entries"]
    if not entries:
        logger.warning("OFAC cache empty — no results")
        return []

    results = []
    name_upper = name.upper()

    for entry in entries:
        best_score = 0
        best_matched_name = ""
        for candidate in entry["all_names"]:
            score = fuzz.token_sort_ratio(name_upper, candidate.upper())
            if score > best_score:
                best_score = score
                best_matched_name = candidate

        if best_score >= FUZZY_THRESHOLD:
            results.append({
                "uid":          entry["uid"],
                "name":         entry["name"],
                "matched_name": best_matched_name,
                "aliases":      entry["aliases"],
                "type":         entry["type"],
                "programs":     entry["programs"],
                "confidence":   round(best_score / 100, 3),
                "source":       "OFAC SDN",
            })

    results.sort(key=lambda x: x["confidence"], reverse=True)
    logger.info(f"OFAC (XML): {len(results)} matches for '{name}'")
    return results[:10]
