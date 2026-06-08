CREDIBILITY_MAP = {
    "ICIJ": 0.95,
    "OCCRP": 0.92,
    "Reuters": 0.90,
    "AP": 0.89,
    "Bloomberg": 0.88,
    "FT": 0.88,
    "WSJ": 0.87,
    "GDELT": 0.75
}

def get_source_credibility(source: str) -> float:
    """
    Get the credibility score for a given source name or URL/domain.
    Normalizes the input and resolves to a default configuration map.
    """
    if not source:
        return CREDIBILITY_MAP["GDELT"]
        
    s = source.lower().strip()
    
    if "icij" in s:
        return CREDIBILITY_MAP["ICIJ"]
    if "occrp" in s:
        return CREDIBILITY_MAP["OCCRP"]
    if "reuters" in s:
        return CREDIBILITY_MAP["Reuters"]
    if "ap" in s or "apnews" in s or "associated press" in s:
        return CREDIBILITY_MAP["AP"]
    if "bloomberg" in s:
        return CREDIBILITY_MAP["Bloomberg"]
    if "ft.com" in s or "financial times" in s or s == "ft":
        return CREDIBILITY_MAP["FT"]
    if "wsj" in s or "wall street journal" in s or s == "wsj.com":
        return CREDIBILITY_MAP["WSJ"]
        
    # Check general substrings against keys
    for key, val in CREDIBILITY_MAP.items():
        if key.lower() in s:
            return val
            
    # Default fallback
    return CREDIBILITY_MAP["GDELT"]
