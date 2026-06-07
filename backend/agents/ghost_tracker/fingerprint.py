from shared.schemas import EntityFingerprint, InvestigateRequest
from shared.utils import generate_entity_id


def build_fingerprint(request: InvestigateRequest) -> EntityFingerprint:
    """
    Build the initial entity fingerprint from the investigation request.
    This is passed to all agents as the shared investigation context.
    """
    return EntityFingerprint(
        entity_id=generate_entity_id(),
        canonical_name=request.name.strip(),
        aliases=[],
        jurisdictions=[request.country_hint] if request.country_hint else [],
        directors=[],
        addresses=[],
        registration_numbers=[],
        sanctions_lists=[],
    )
