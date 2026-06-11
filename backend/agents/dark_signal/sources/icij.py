"""
backend/agents/dark_signal/sources/icij.py

ICIJ Offshore Leaks database source for the Dark Signal agent.
Uses the local parquet snapshot via data_loader as primary path (instant, no network).
Falls back to the fabric pipeline helper if available.
"""

from shared.logger import get_logger

logger = get_logger(__name__)


async def search_icij(name: str) -> list[dict]:
    """
    Search ICIJ Offshore Leaks database (Panama Papers, Pandora Papers, etc.)

    Primary:  data_loader.search_icij()  — instant local parquet search
    Fallback: fabric.pipeline helper     — if data_loader not ready yet
    """
    logger.info(f"ICIJ search: '{name}'")
    results: list[dict] = []

    # ── Primary: local parquet via data_loader ────────────────────────────────
    try:
        from shared.data_loader import search_icij as _local_search
        matches = _local_search(name, threshold=0.70)
        for m in matches:
            results.append({
                "source":         "ICIJ",
                "title":          f"ICIJ Match: {m['name']}",
                "url":            m.get("url"),
                "entity":         m["name"],
                "country":        m.get("countries", "unknown"),
                "summary":        (
                    f"Found in ICIJ Offshore Leaks database. "
                    f"Dataset: {m.get('dataset', 'N/A')}. "
                    f"Node ID: {m.get('node_id', 'N/A')}."
                ),
                "confidence":     m["confidence"],
                "published_date": None,
            })
        if results:
            logger.info(f"ICIJ (local parquet): {len(results)} matches for '{name}'")
            return results
    except Exception as exc:
        logger.warning(f"ICIJ local parquet path failed, trying fabric helper: {exc}")

    # ── Fallback: fabric pipeline helper ─────────────────────────────────────
    try:
        from fabric.pipeline import query_icij_by_name
        matches = await query_icij_by_name(name, threshold=70.0)
        for m in matches:
            results.append({
                "source":         "ICIJ",
                "title":          f"ICIJ Match: {m.get('name')}",
                "url":            (
                    f"https://offshoreleaks.icij.org/nodes/{m.get('node_id')}"
                    if m.get("node_id") else None
                ),
                "entity":         m.get("name"),
                "country":        m.get("countries") or m.get("jurisdiction") or "unknown",
                "summary":        (
                    f"Found in ICIJ database. "
                    f"Dataset: {m.get('dataset')}. "
                    f"Node ID: {m.get('node_id')}."
                ),
                "confidence":     m.get("match_score", 0.0),
                "published_date": None,
            })
    except Exception as exc:
        logger.error(f"ICIJ fabric fallback also failed: {exc}")

    return results
