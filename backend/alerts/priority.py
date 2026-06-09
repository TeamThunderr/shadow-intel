from shared.schemas import AlertPayload, RiskLevel
from shared.logger import get_logger

logger = get_logger(__name__)

def determine_alert_priority(confidence: float) -> RiskLevel:
    """
    Classify alert severity based on confidence score (0.0 to 1.0).
    - 0-40%: Low (Log Only)
    - 41-70%: Medium (Teams Alert)
    - 71-85%: High (Teams + Email)
    - 86-100%: Critical (Teams + Email + Priority Flag)
    """
    percentage = confidence * 100
    if percentage <= 40:
        return RiskLevel.low
    elif percentage <= 70:
        return RiskLevel.medium
    elif percentage <= 85:
        return RiskLevel.high
    else:
        return RiskLevel.critical

def route_alert(alert: AlertPayload) -> dict:
    """
    Determine which channels should receive this alert.
    Returns a dict of boolean flags for each delivery channel.
    """
    # Overwrite the risk_level based on our strict Priority Engine rules
    alert.risk_level = determine_alert_priority(alert.confidence)
    
    routing = {
        "log_only": False,
        "send_teams": False,
        "send_email": False,
        "is_priority": False
    }
    
    if alert.risk_level == RiskLevel.low:
        routing["log_only"] = True
    elif alert.risk_level == RiskLevel.medium:
        routing["send_teams"] = True
    elif alert.risk_level == RiskLevel.high:
        routing["send_teams"] = True
        routing["send_email"] = True
    elif alert.risk_level == RiskLevel.critical:
        routing["send_teams"] = True
        routing["send_email"] = True
        routing["is_priority"] = True
        
    logger.info(f"Routing for entity '{alert.entity_name}' (Score: {alert.confidence*100:.0f}%): {routing}")
    return routing
