import asyncio
import os
import sys

# Add backend to path so imports work
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "backend"))

from shared.schemas import AlertPayload, RiskLevel
from alerts.pipeline import process_alert
from datetime import datetime

async def test_alert():
    print("\n--- [ Shadow Intel Task C Test ] ---\n")
    
    alert = AlertPayload(
        entity_id="test-entity-123",
        entity_name="Viktor Bout Global Holdings",
        match_event="New Corporate Registration detected in Panama registry",
        confidence=0.92, # This triggers CRITICAL routing (Teams + Email)
        jurisdiction="Panama",
        risk_level=RiskLevel.critical,
        top_evidence=[
            "Exact name match found in Panama registry.",
            "Registration agent flagged for prior sanctions evasion.",
            "Address matches known shell company cluster."
        ],
        report_url="http://localhost:5173/investigate/test-entity-123",
        timestamp=datetime.utcnow()
    )
    
    print(f"Triggering Process Alert for: {alert.entity_name} (Confidence: {alert.confidence*100}%)")
    print("This should route to Microsoft Teams AND Outlook because it is >85% confidence.\n")
    
    results = await process_alert(alert, analyst_email="analyst@example.com")
    
    print("\n--- [ Delivery Results ] ---")
    print(f"Overall Status: {results['overall_status']}")
    print(f"Teams Success: {results['teams_success']}")
    print(f"Email Success: {results['email_success']}")
    
    print("\nCheck the terminal logs above to see the routing and JSON card generation process!")

if __name__ == "__main__":
    asyncio.run(test_alert())
