import asyncio
from agents.base import BaseAgent
from shared.schemas import AgentResponse, EntityFingerprint, AlertPayload, RiskLevel, EvidenceItem
from agents.resurface.monitors import OpenCorporatesMonitor, WhoisMonitor
from agents.resurface.similarity import calculate_similarity_score
from agents.resurface.store import AlertStore

class ResurfaceAlertEngine(BaseAgent):
    """
    Monitors for new registrations matching entity fingerprint.
    Fires Teams/Outlook alert when confidence exceeds threshold.
    """

    @property
    def module_name(self) -> str:
        return "resurface_engine"

    async def run(self, fingerprint: EntityFingerprint, threshold: float = 0.80) -> AgentResponse:
        self.logger.info(f"Running resurface check for: {fingerprint.canonical_name}")
        
        corp_monitor = OpenCorporatesMonitor()
        whois_monitor = WhoisMonitor()
        
        # 1 & 2. Check monitors
        corp_hits, whois_hits = await asyncio.gather(
            corp_monitor.check_new_registrations(fingerprint),
            whois_monitor.check_new_domains(fingerprint)
        )
        
        evidence = []
        highest_score = 0.0
        alerts_generated = []
        
        # 3. Score matches against fingerprint
        for hit in corp_hits + whois_hits:
            score = calculate_similarity_score(fingerprint, hit)
            if score > highest_score:
                highest_score = score
                
            # 4. If score > threshold: trigger alerts
            if score >= threshold:
                alert = AlertPayload(
                    entity_id=fingerprint.entity_id,
                    entity_name=fingerprint.canonical_name,
                    confidence=score,
                    risk_level=RiskLevel.high if score > 0.9 else RiskLevel.medium,
                    match_event=hit.get("source", "Unknown"),
                    jurisdiction=hit.get("jurisdiction", "Unknown"),
                    top_evidence=[str(hit)]
                )
                
                # Write to AlertLog
                store = AlertStore()
                await store.write_alert(alert)
                alerts_generated.append(alert)
                
                # Add to evidence list for AgentResponse
                evidence.append(EvidenceItem(
                    source=hit.get("source", "Unknown"),
                    type="resurface_match",
                    detail=f"Detected new activity matching fingerprint with {score*100:.1f}% confidence.",
                    confidence=score
                ))

        return AgentResponse(
            module=self.module_name,
            entity_id=fingerprint.entity_id,
            risk_score=highest_score,
            evidence=evidence,
            data={
                "resurface_events": corp_hits + whois_hits,
                "alerts_generated": [a.model_dump(mode="json") for a in alerts_generated]
            }
        )
