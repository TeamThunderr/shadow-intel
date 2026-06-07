from azure.ai.inference import ChatCompletionsClient
from azure.ai.inference.models import SystemMessage, UserMessage
from azure.core.credentials import AzureKeyCredential
from shared.config import get_settings
from shared.logger import get_logger

logger = get_logger(__name__)


class FoundryOrchestrator:
    """
    Foundry IQ — uses Azure AI Foundry to generate narrative summary
    from merged agent evidence.
    """

    def __init__(self):
        settings = get_settings()
        self.client = ChatCompletionsClient(
            endpoint=settings.azure_foundry_endpoint,
            credential=AzureKeyCredential(settings.azure_foundry_api_key),
        )
        self.deployment = settings.azure_foundry_deployment

    async def generate_narrative(self, entity_name: str, merged_evidence: list[dict]) -> str:
        """
        Call Foundry IQ to generate a detective-style investigation summary.
        Returns plain-language narrative explaining the evidence chain.
        """
        evidence_text = "\n".join([
            f"- [{e.get('source')}] {e.get('detail')}"
            for e in merged_evidence[:20]
        ])

        prompt = f"""You are a financial crime intelligence analyst reviewing evidence about an entity.

Entity: {entity_name}

Evidence collected:
{evidence_text}

Write a concise detective-style investigation summary (3-5 paragraphs):
1. What was found and how suspicious it is
2. The key connections between pieces of evidence
3. The most likely explanation for the patterns observed
4. A clear risk assessment conclusion

Be factual, specific, and write in plain language a journalist could publish."""

        try:
            response = self.client.complete(
                messages=[
                    SystemMessage(content="You are a financial crime intelligence analyst. Be factual and concise."),
                    UserMessage(content=prompt),
                ],
                model=self.deployment,
                max_tokens=800,
            )
            return response.choices[0].message.content
        except Exception as e:
            logger.error(f"Foundry IQ narrative generation failed: {e}")
            return f"Investigation of {entity_name} — narrative generation unavailable."
