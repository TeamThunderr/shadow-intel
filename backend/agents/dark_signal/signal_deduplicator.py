from rapidfuzz import fuzz
from agents.dark_signal.signal_models import DarkSignal
from fabric.pipeline import normalize_entity_name

def are_signals_duplicate(s1: DarkSignal, s2: DarkSignal) -> bool:
    """
    Check if two signals represent the same article or event.
    Returns True if duplicate, False otherwise.
    """
    # 1. Exact URL match (if URLs are available)
    if s1.url and s2.url:
        u1 = s1.url.strip().lower()
        u2 = s2.url.strip().lower()
        if u1 == u2:
            return True
            
    # 2. Fuzzy Entity Name + Fuzzy Title Match
    # Normalize entities to ensure clean comparison
    ent1 = normalize_entity_name(s1.entity)
    ent2 = normalize_entity_name(s2.entity)
    
    entity_sim = fuzz.token_sort_ratio(ent1, ent2)
    if entity_sim >= 85:
        # Check title similarity
        title_sim = fuzz.token_sort_ratio(s1.title.lower(), s2.title.lower())
        if title_sim >= 80:
            return True
            
    return False

def deduplicate_signals(signals: list[DarkSignal]) -> list[DarkSignal]:
    """
    Deduplicates a list of DarkSignal objects.
    Sorts signals by relevance score (descending) so the highest scoring signal 
    is retained, discarding duplicates.
    """
    if not signals:
        return []
        
    # Sort descending by relevance score, then credibility, then confidence
    sorted_signals = sorted(
        signals,
        key=lambda x: (x.relevance_score, x.credibility, x.confidence),
        reverse=True
    )
    
    deduplicated: list[DarkSignal] = []
    for sig in sorted_signals:
        is_dup = False
        for existing in deduplicated:
            if are_signals_duplicate(sig, existing):
                is_dup = True
                break
        if not is_dup:
            deduplicated.append(sig)
            
    return deduplicated
