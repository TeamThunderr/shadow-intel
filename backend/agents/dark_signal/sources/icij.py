from shared.logger import get_logger

logger = get_logger(__name__)

ICIJ_SEARCH_URL = "https://offshoreleaks.icij.org/api/search"


async def search_icij(name: str) -> list[dict]:
    """
    Search ICIJ Offshore Leaks database (Panama Papers, Pandora Papers, etc.)
    Uses backend.fabric.pipeline.query_icij_by_name() helper.
    Only falls back to direct parquet loading if the helper is unavailable/fails.
    """
    logger.info(f"Searching ICIJ for: {name}")
    results = []
    
    try:
        from fabric.pipeline import query_icij_by_name
        matches = await query_icij_by_name(name, threshold=70.0)
        for m in matches:
            results.append({
                "source": "ICIJ",
                "title": f"ICIJ Match: {m.get('name')}",
                "url": f"https://offshoreleaks.icij.org/nodes/{m.get('node_id')}" if m.get('node_id') else None,
                "entity": m.get('name'),
                "country": m.get('countries') or m.get('jurisdiction') or "unknown",
                "summary": f"Found in ICIJ database. Dataset: {m.get('dataset')}. Node ID: {m.get('node_id')}.",
                "confidence": m.get('match_score', 0.0),
                "published_date": None
            })
        return results
    except Exception as e:
        logger.error(f"query_icij_by_name helper failed/unavailable, falling back to direct parquet: {e}")
        
    try:
        from fabric.pipeline import load_local, normalize_entity_name
        from rapidfuzz import fuzz
        
        query_normalized = normalize_entity_name(name)
        if not query_normalized:
            return []
            
        matches = []
        
        df_entities = load_local("icij_entities")
        if df_entities is not None:
            for _, row in df_entities.iterrows():
                row_name = str(row.get('name', ''))
                row_normalized = normalize_entity_name(row_name)
                if not row_normalized:
                    continue
                
                token_sort_ratio = fuzz.token_sort_ratio(query_normalized, row_normalized)
                token_set_ratio = fuzz.token_set_ratio(query_normalized, row_normalized)
                partial_ratio = fuzz.partial_ratio(query_normalized, row_normalized)
                confidence = 0.5 * token_sort_ratio + 0.3 * token_set_ratio + 0.2 * partial_ratio
                
                if confidence >= 70.0:
                    matches.append({
                        "name": row_name,
                        "node_id": str(row.get('node_id', '')),
                        "countries": str(row.get('countries', '')),
                        "dataset": str(row.get('sourceID', '')),
                        "match_score": confidence / 100.0
                    })
                    
        df_officers = load_local("icij_officers")
        if df_officers is not None:
            for _, row in df_officers.iterrows():
                row_name = str(row.get('name', ''))
                row_normalized = normalize_entity_name(row_name)
                if not row_normalized:
                    continue
                
                token_sort_ratio = fuzz.token_sort_ratio(query_normalized, row_normalized)
                token_set_ratio = fuzz.token_set_ratio(query_normalized, row_normalized)
                partial_ratio = fuzz.partial_ratio(query_normalized, row_normalized)
                confidence = 0.5 * token_sort_ratio + 0.3 * token_set_ratio + 0.2 * partial_ratio
                
                if confidence >= 70.0:
                    matches.append({
                        "name": row_name,
                        "node_id": str(row.get('node_id', '')),
                        "countries": str(row.get('countries', '')),
                        "dataset": str(row.get('sourceID', '')),
                        "match_score": confidence / 100.0
                    })
                    
        for m in matches:
            results.append({
                "source": "ICIJ",
                "title": f"ICIJ Match: {m['name']}",
                "url": f"https://offshoreleaks.icij.org/nodes/{m['node_id']}" if m['node_id'] else None,
                "entity": m['name'],
                "country": m['countries'] or "unknown",
                "summary": f"Found in ICIJ database. Dataset: {m['dataset']}. Node ID: {m['node_id']}.",
                "confidence": m['match_score'],
                "published_date": None
            })
            
    except Exception as ex:
        logger.error(f"Fallback direct parquet loading failed: {ex}")
        
    return results
