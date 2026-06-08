import difflib
from typing import List
from shared.schemas import EntityFingerprint

def calculate_similarity_score(fingerprint: EntityFingerprint, event_data: dict) -> float:
    """
    Calculates similarity between a stored fingerprint and a new event.
    Returns a score between 0.0 and 1.0.
    
    Factors:
    - Name Similarity: 40%
    - Director Overlap: 25%
    - Jurisdiction Match: 15%
    - Domain Match: 10%
    - Wallet Match: 10%
    """
    total_score = 0.0
    
    # 1. Name Similarity (40%)
    event_names = [event_data.get("name", "")] + event_data.get("aliases", [])
    fingerprint_names = [fingerprint.canonical_name] + fingerprint.aliases
    name_score = _best_match_score(fingerprint_names, event_names)
    total_score += (name_score * 0.40)
    
    # 2. Director Overlap (25%)
    event_directors = event_data.get("directors", [])
    if fingerprint.directors and event_directors:
        dir_score = _overlap_score(fingerprint.directors, event_directors)
        total_score += (dir_score * 0.25)
    
    # 3. Jurisdiction Match (15%)
    event_jurisdictions = event_data.get("jurisdictions", [])
    if fingerprint.jurisdictions and event_jurisdictions:
        jur_score = _overlap_score(fingerprint.jurisdictions, event_jurisdictions)
        total_score += (jur_score * 0.15)
        
    # 4. Domain Match (10%)
    event_domains = event_data.get("domains", [])
    # If fingerprint doesn't explicitly have domains, we might fuzzy match domains to name
    if event_domains:
        domain_score = _best_match_score(fingerprint_names, event_domains)
        total_score += (domain_score * 0.10)
        
    # 5. Wallet Match (10%)
    event_wallets = event_data.get("wallets", [])
    # For now, we simulate wallets matching
    if event_wallets:
        total_score += (0.0) # Not fully implemented in fingerprint model
        
    return min(total_score, 1.0)

def _best_match_score(list1: List[str], list2: List[str]) -> float:
    if not list1 or not list2:
        return 0.0
    best_score = 0.0
    for s1 in list1:
        if not s1: continue
        for s2 in list2:
            if not s2: continue
            score = difflib.SequenceMatcher(None, s1.lower(), s2.lower()).ratio()
            if score > best_score:
                best_score = score
    return best_score

def _overlap_score(list1: List[str], list2: List[str]) -> float:
    if not list1 or not list2:
        return 0.0
    set1 = {s.lower() for s in list1 if s}
    set2 = {s.lower() for s in list2 if s}
    if not set1 or not set2:
        return 0.0
    
    intersection = set1.intersection(set2)
    # Score based on proportion of list2 (the new event) found in list1 (the fingerprint)
    # Alternatively, just 1.0 if there's any overlap for a simpler model. Let's use proportional.
    return len(intersection) / float(len(set2))
