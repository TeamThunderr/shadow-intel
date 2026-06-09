from shared.schemas import AlertPayload
from shared.logger import get_logger
from alerts.priority import route_alert
from alerts.teams import send_teams_alert
from alerts.outlook import send_outlook_alert
from alerts.fabric_log import write_alert_log, update_alert_status
from shared.config import get_settings

logger = get_logger(__name__)

async def process_alert(alert: AlertPayload, analyst_email: str = None) -> dict:
    """
    Master orchestration workflow for delivering a Shadow Intel alert.
    
    Flow:
    1. Determine Priority
    2. Write to Fabric (queued)
    3. Dispatch to Teams/Email based on routing
    4. Update Fabric (delivered/failed)
    """
    logger.info(f"Processing new alert for: {alert.entity_name} (Score: {alert.confidence*100:.1f}%)")
    
    routing = route_alert(alert)
    
    alert_id = await write_alert_log(alert, routing, delivery_status="queued")
    
    delivery_results = {
        "teams_success": None,
        "email_success": None,
        "overall_status": "queued"
    }
    
    if routing.get("log_only"):
        await update_alert_status(alert_id, "logged")
        delivery_results["overall_status"] = "logged"
        return delivery_results

    # Teams Delivery
    if routing.get("send_teams"):
        try:
            teams_ok = await send_teams_alert(alert)
            delivery_results["teams_success"] = teams_ok
        except Exception as e:
            logger.error(f"Teams delivery crashed for {alert_id}: {e}")
            delivery_results["teams_success"] = False

    # Email Delivery
    if routing.get("send_email"):
        target_email = analyst_email or get_settings().graph_sender_email
        if target_email:
            try:
                email_ok = await send_outlook_alert(alert, target_email)
                delivery_results["email_success"] = email_ok
            except Exception as e:
                logger.error(f"Email delivery crashed for {alert_id}: {e}")
                delivery_results["email_success"] = False
        else:
            logger.warning("No recipient email available for Outlook delivery.")
            delivery_results["email_success"] = False

    # Determine final status
    # If any required channel succeeded, we consider it partially delivered at least
    failed = False
    if routing.get("send_teams") and not delivery_results["teams_success"]:
        failed = True
    if routing.get("send_email") and not delivery_results["email_success"]:
        failed = True
        
    final_status = "failed" if failed else "delivered"
    if failed and (delivery_results.get("teams_success") or delivery_results.get("email_success")):
        final_status = "partial_failure"
        
    delivery_results["overall_status"] = final_status
    
    # Update Fabric with final status
    await update_alert_status(alert_id, final_status)
    
    logger.info(f"Alert {alert_id} processing complete. Status: {final_status}")
    
    return delivery_results
