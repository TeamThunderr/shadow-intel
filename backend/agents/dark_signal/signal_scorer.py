from datetime import datetime, timezone
from typing import Optional
from agents.dark_signal.signal_models import DarkSignal
from agents.dark_signal.source_credibility import get_source_credibility

investigative_keywords = [
    "corruption",
    "sanctions",
    "fraud",
    "money laundering",
    "offshore",
    "shell company",
    "bribery",
    "embezzlement",
    "tax evasion",
    "leak",
    "oligarch"
]

def calculate_recency_score(published_date: Optional[datetime]) -> float:
    """
    Calculate recency score between 0.0 and 1.0.
    If no date is present, default to a neutral 0.5.
    Otherwise, older dates decay in value.
    """
    if not published_date:
        return 0.5
        
    # Standardize published_date timezone for comparison
    now = datetime.now(timezone.utc)
    if published_date.tzinfo is None:
        published_date = published_date.replace(tzinfo=timezone.utc)
        
    delta = now - published_date
    days = max(0, delta.days)
    
    if days <= 7:
        return 1.0
    elif days <= 30:
        return 0.8
    elif days <= 90:
        return 0.6
    elif days <= 365:
        return 0.4
    else:
        return 0.2

def score_signal(signal: DarkSignal) -> float:
    """
    Calculate and update the relevance score of a DarkSignal.
    Formula:
    relevance_score = (
        entity_match * 0.40 +
        credibility * 0.25 +
        recency * 0.20 +
        keyword_match * 0.15
    )
    Modifies the signal's internal score fields and returns the relevance score.
    """
    # 1. Entity Match (confidence)
    entity_match = signal.confidence
    
    # 2. Credibility
    credibility = get_source_credibility(signal.source)
    signal.credibility = credibility
    
    # 3. Recency
    recency = calculate_recency_score(signal.published_date)
    signal.recency_score = recency
    
    # 4. Keyword Match
    keyword_match = 0.0
    text_to_check = (signal.title + " " + signal.summary).lower()
    for kw in investigative_keywords:
        if kw in text_to_check:
            keyword_match = 1.0
            break
            
    # Calculate score
    score = (
        entity_match * 0.40 +
        credibility * 0.25 +
        recency * 0.20 +
        keyword_match * 0.15
    )
    
    # Cap to range 0.0 - 1.0
    score = max(0.0, min(1.0, score))
    signal.relevance_score = score
    
    return score
