from agents.dark_signal.signal_models import DarkSignal

def calculate_osint_risk(signals: list[DarkSignal]) -> tuple[float, str]:
    """
    Calculate the overall OSINT risk score and level from a list of DarkSignals.
    Formula:
    risk_score = signal_count * avg_credibility * avg_relevance * recency_weight
    
    Returns:
      (normalized_risk_score, risk_level)
      Where risk_score is bounded in [0.0, 1.0] and risk_level is LOW, MEDIUM, or HIGH.
    """
    if not signals:
        return 0.0, "LOW"
        
    signal_count = len(signals)
    avg_credibility = sum(s.credibility for s in signals) / signal_count
    avg_relevance = sum(s.relevance_score for s in signals) / signal_count
    recency_weight = sum(s.recency_score for s in signals) / signal_count
    
    raw_score = signal_count * avg_credibility * avg_relevance * recency_weight
    
    # Normalize between 0.0 and 1.0
    normalized_score = max(0.0, min(1.0, raw_score))
    
    if normalized_score <= 0.30:
        level = "LOW"
    elif normalized_score <= 0.60:
        level = "MEDIUM"
    else:
        level = "HIGH"
        
    return normalized_score, level
