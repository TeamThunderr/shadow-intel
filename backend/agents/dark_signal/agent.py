import asyncio
from agents.base import BaseAgent
from shared.schemas import AgentResponse, EntityFingerprint, EvidenceItem, AgentStatus
from shared.logger import get_logger

from agents.dark_signal.signal_models import DarkSignal
from agents.dark_signal.signal_scorer import score_signal
from agents.dark_signal.signal_deduplicator import deduplicate_signals
from agents.dark_signal.osint_risk import calculate_osint_risk

from agents.dark_signal.sources.icij import search_icij
from agents.dark_signal.sources.occrp import search_occrp
from agents.dark_signal.sources.gdelt import search_gdelt

logger = get_logger(__name__)


class DarkSignalMonitor(BaseAgent):
    """
    Cross-references entity against leaked databases, OCCRP, and OSINT news feeds.
    Owner: Person 3
    """

    @property
    def module_name(self) -> str:
        return "dark_signal"

    async def run(self, fingerprint: EntityFingerprint) -> AgentResponse:
        logger.info(f"Running DSM agent for: {fingerprint.canonical_name}")
        
        # 1. Expand and unique-ify search names (canonical name + aliases)
        search_names = {fingerprint.canonical_name}
        if fingerprint.aliases:
            for alias in fingerprint.aliases:
                if alias.strip():
                    search_names.add(alias.strip())
                    
        # 2. Query sources in parallel with Exception safety
        tasks = []
        for name in search_names:
            tasks.append(search_icij(name))
            tasks.append(search_occrp(name))
            tasks.append(search_gdelt(name))
            
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        all_raw_signals = []
        for idx, r in enumerate(results):
            if isinstance(r, Exception):
                logger.error(f"A search query task failed: {r}")
            elif r:
                all_raw_signals.extend(r)
                
        # 3. Convert to DarkSignal models, score relevance, and filter news signals by MIN_RELEVANCE = 0.55
        scored_signals = []
        for sig in all_raw_signals:
            try:
                ds = DarkSignal(
                    source=sig.get("source", "unknown"),
                    title=sig.get("title", "No Title"),
                    summary=sig.get("summary", ""),
                    url=sig.get("url"),
                    entity=sig.get("entity", fingerprint.canonical_name),
                    confidence=sig.get("confidence", 0.5),
                    published_date=sig.get("published_date")
                )
                
                # Score relevance
                score_signal(ds)
                
                # Apply MIN_RELEVANCE filter for news articles (GDELT and other publishers, excluding ICIJ & OCCRP)
                is_news = ds.source not in ("ICIJ", "OCCRP")
                if is_news and ds.relevance_score < 0.55:
                    logger.debug(f"Filtering out low-relevance news: {ds.title} (Score: {ds.relevance_score:.2f})")
                    continue
                    
                scored_signals.append(ds)
            except Exception as e:
                logger.error(f"Error normalizing raw signal to DarkSignal: {e}")
                
        # 4. Deduplicate signals
        deduped_signals = deduplicate_signals(scored_signals)
        logger.info(f"Deduplicated {len(scored_signals)} signals down to {len(deduped_signals)} unique signals.")
        
        # 5. Calculate OSINT risk score
        risk_score, risk_level = calculate_osint_risk(deduped_signals)
        logger.info(f"Calculated OSINT risk score: {risk_score:.3f} ({risk_level})")
        
        # 6. Format EvidenceItems
        evidence_items = []
        for ds in deduped_signals:
            contribution = ds.credibility * ds.relevance_score * ds.recency_score
            evidence_item = EvidenceItem(
                source=ds.source,
                type="dark_signal",
                detail=f"[{ds.title}] {ds.summary} (Match: {ds.confidence:.2f}, Credibility: {ds.credibility:.2f}, Relevance: {ds.relevance_score:.2f}, Risk Contribution: {contribution:.2f})",
                url=ds.url,
                date=ds.published_date,
                confidence=ds.confidence
            )
            evidence_items.append(evidence_item)
            
        # 7. Construct AgentResponse
        return AgentResponse(
            module=self.module_name,
            entity_id=fingerprint.entity_id,
            status=AgentStatus.complete,
            risk_score=risk_score,
            evidence=evidence_items,
            data={
                "signals": [s.model_dump() for s in deduped_signals],
                "risk_level": risk_level,
                "signal_count": len(deduped_signals)
            }
        )

