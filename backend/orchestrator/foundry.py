"""
Foundry IQ — Azure AI Foundry SDK Integration
This is Shadow Intel's primary Microsoft IQ showcase.

Setup:
1. Create an Azure AI Foundry project at https://ai.azure.com
2. Deploy a gpt-4o model
3. Copy the endpoint + API key to .env as:
     AZURE_FOUNDRY_ENDPOINT=https://<resource>.openai.azure.com/
     AZURE_FOUNDRY_API_KEY=<key>
     AZURE_FOUNDRY_DEPLOYMENT=gpt-4o

Free tier: New Azure accounts receive $200 credit —
           sufficient for 10,000+ Foundry IQ calls at hackathon scale.

Graceful fallback:
  If credentials are absent or the call fails, a deterministic
  template-based narrative is produced so the rest of the pipeline
  never blocks or crashes.
"""

import asyncio

from azure.ai.inference import ChatCompletionsClient
from azure.ai.inference.models import SystemMessage, UserMessage
from azure.core.credentials import AzureKeyCredential
from azure.core.exceptions import AzureError

from shared.config import get_settings
from shared.schemas import EvidenceItem, RiskLevel
from shared.logger import get_logger

logger = get_logger(__name__)

# ─── Prompt templates ─────────────────────────────────────────────────────────

SYSTEM_PROMPT = """You are a senior financial crime intelligence analyst at a global \
investigative organisation. You review evidence collected by automated agents and \
produce clear, factual investigation summaries.

Your summaries are read by journalists, compliance officers, and policy researchers. \
Write with precision. Be factual. Do not speculate beyond what the evidence supports. \
Use plain language. Flag the most important findings prominently."""


def _build_evidence_text(evidence: list[EvidenceItem]) -> str:
    """Format evidence items into a structured block for the LLM prompt."""
    if not evidence:
        return "No evidence collected."

    lines: list[str] = []
    # Group by source module for clearer reading
    by_source: dict[str, list[EvidenceItem]] = {}
    for e in evidence:
        by_source.setdefault(e.source, []).append(e)

    for source, items in by_source.items():
        lines.append(f"\n[{source.upper()}]")
        for item in sorted(items, key=lambda x: x.confidence, reverse=True)[:5]:
            lines.append(f"  • {item.detail} (confidence: {item.confidence:.0%})")

    return "\n".join(lines)


def _build_investigation_prompt(
    entity_name: str,
    risk_level: RiskLevel,
    unified_confidence: float,
    evidence: list[EvidenceItem],
    source_breakdown: dict,
) -> str:
    """Compose the full user-turn prompt for Foundry IQ."""
    evidence_text = _build_evidence_text(evidence)
    active_sources = [k for k, v in source_breakdown.items() if v > 0]

    return f"""INVESTIGATION REPORT REQUEST

Entity under investigation: {entity_name}
Overall risk assessment: {risk_level.value.upper()}
Unified confidence score: {unified_confidence:.0%}
Active intelligence sources: {', '.join(active_sources) if active_sources else 'None'}

EVIDENCE COLLECTED:
{evidence_text}

---

Please write an investigation summary with these four sections:

1. OVERVIEW (2-3 sentences)
   What was found and how significant it is overall.

2. KEY FINDINGS (3-5 bullet points)
   The most important individual pieces of evidence.
   Be specific — name the sources, jurisdictions, and patterns detected.

3. CONNECTIONS (1-2 paragraphs)
   How the findings from different sources link together.
   What pattern do they collectively suggest?

4. RISK CONCLUSION (1 paragraph)
   Overall risk assessment. What should the reader do with this information?
   Who are the relevant authorities or publications this should be referred to?

Keep the entire summary under 400 words. Be direct."""


# ─── Foundry orchestrator ─────────────────────────────────────────────────────

class FoundryOrchestrator:
    """
    Foundry IQ — Azure AI Foundry reasoning engine.

    Generates a structured detective-style narrative from the merged
    agent evidence set. This is the primary Microsoft IQ showcase for
    the hackathon judges.

    The client is lazily initialised so that the server can start
    cleanly even if Azure credentials are missing.
    """

    def __init__(self) -> None:
        self.settings = get_settings()
        self._client: ChatCompletionsClient | None = None

    def _get_client(self) -> ChatCompletionsClient | None:
        """Lazily create and cache the Azure ChatCompletionsClient."""
        if self._client is not None:
            return self._client

        endpoint = self.settings.azure_foundry_endpoint
        api_key = self.settings.azure_foundry_api_key

        if not endpoint or not api_key:
            logger.warning(
                "Foundry IQ: Azure credentials not configured. "
                "Set AZURE_FOUNDRY_ENDPOINT and AZURE_FOUNDRY_API_KEY in .env — "
                "using fallback narrative instead."
            )
            return None

        try:
            self._client = ChatCompletionsClient(
                endpoint=endpoint,
                credential=AzureKeyCredential(api_key),
            )
            logger.info("Foundry IQ: Azure ChatCompletionsClient initialised")
            return self._client
        except Exception as exc:
            logger.error(f"Foundry IQ: failed to initialise client — {exc}")
            return None

    async def generate_narrative(
        self,
        entity_name: str,
        risk_level: RiskLevel,
        unified_confidence: float,
        evidence: list[EvidenceItem],
        source_breakdown: dict,
    ) -> str:
        """
        Call Azure AI Foundry to generate the investigation narrative.

        The Azure AI Inference SDK uses a synchronous `complete()` call,
        so we offload it to the default thread-pool executor to avoid
        blocking the asyncio event loop.

        Falls back to a deterministic template if:
          - Credentials are absent
          - The Azure call raises an error
        """
        client = self._get_client()

        if client is None:
            return self._fallback_narrative(
                entity_name, risk_level, unified_confidence, evidence
            )

        prompt = _build_investigation_prompt(
            entity_name, risk_level, unified_confidence,
            evidence, source_breakdown,
        )

        try:
            loop = asyncio.get_event_loop()
            response = await loop.run_in_executor(
                None,
                lambda: client.complete(
                    messages=[
                        SystemMessage(content=SYSTEM_PROMPT),
                        UserMessage(content=prompt),
                    ],
                    model=self.settings.azure_foundry_deployment,
                    max_tokens=600,
                    temperature=0.3,  # low temperature → factual, reproducible output
                ),
            )

            narrative = response.choices[0].message.content.strip()
            logger.info(
                f"Foundry IQ: narrative generated | "
                f"tokens_used={response.usage.total_tokens} | "
                f"entity='{entity_name}'"
            )
            return narrative

        except AzureError as exc:
            logger.error(f"Foundry IQ: Azure error — {exc}")
            return self._fallback_narrative(
                entity_name, risk_level, unified_confidence, evidence
            )
        except Exception as exc:
            logger.error(f"Foundry IQ: unexpected error — {exc}")
            return self._fallback_narrative(
                entity_name, risk_level, unified_confidence, evidence
            )

    # ── Fallback ──────────────────────────────────────────────────────────────

    def _fallback_narrative(
        self,
        entity_name: str,
        risk_level: RiskLevel,
        unified_confidence: float,
        evidence: list[EvidenceItem],
    ) -> str:
        """
        Template-based narrative for when Foundry IQ is unavailable.
        Still produces a complete, readable report section.
        """
        top_evidence = sorted(evidence, key=lambda e: e.confidence, reverse=True)[:5]
        bullet_lines = "\n".join(
            f"  • [{e.source}] {e.detail}" for e in top_evidence
        ) or "  • No significant findings detected across monitored sources."

        return (
            f"OVERVIEW\n"
            f"Investigation of '{entity_name}' returned a "
            f"{risk_level.value.upper()} risk assessment with a unified "
            f"confidence score of {unified_confidence:.0%} across all "
            f"intelligence sources.\n\n"
            f"KEY FINDINGS\n"
            f"{bullet_lines}\n\n"
            f"CONNECTIONS\n"
            f"The evidence collected across sanctions lists, corporate registries, "
            f"and open intelligence sources has been aggregated and weighted. Each "
            f"source contributes independently scored evidence to the overall risk "
            f"profile. Cross-source corroboration raises the overall confidence.\n\n"
            f"RISK CONCLUSION\n"
            f"Based on the available evidence, '{entity_name}' has been assessed as "
            f"{risk_level.value.upper()} risk. This report should be reviewed by a "
            f"qualified compliance officer or investigative journalist before any "
            f"action is taken. All data is sourced from publicly available databases.\n\n"
            f"[Powered by Shadow Intel | Foundry IQ narrative unavailable — "
            f"configure AZURE_FOUNDRY_ENDPOINT and AZURE_FOUNDRY_API_KEY to enable]"
        )
