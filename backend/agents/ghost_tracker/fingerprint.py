"""
Entity fingerprint builder.
The fingerprint is created once by Ghost Tracker and passed
to every subsequent agent as their primary input context.
"""

from shared.schemas import EntityFingerprint, InvestigateRequest
from shared.utils import generate_entity_id


def build_fingerprint(request: InvestigateRequest) -> EntityFingerprint:
    """
    Build the initial entity fingerprint from the user's investigation request.
    This is passed to all agents as the shared investigation context.
    Other agents enrich this fingerprint as they run.
    """
    jurisdictions = []
    if request.country_hint:
        jurisdictions.append(request.country_hint.upper())

    return EntityFingerprint(
        entity_id=generate_entity_id(),
        canonical_name=request.name.strip(),
        aliases=[],
        jurisdictions=jurisdictions,
        directors=[],
        addresses=[],
        registration_numbers=[],
        sanctions_lists=[],
    )


def enrich_fingerprint(
    fingerprint: EntityFingerprint,
    ofac_results: list[dict],
    un_results: list[dict],
    os_results: list[dict],
    corp_results: list[dict],
) -> EntityFingerprint:
    """
    Enrich the fingerprint with data discovered by Ghost Tracker sources.
    Merges aliases, jurisdictions, and sanctions list memberships.
    Returns the enriched fingerprint — this is what gets passed to other agents.
    """
    aliases = set(fingerprint.aliases)
    jurisdictions = set(fingerprint.jurisdictions)
    sanctions_lists = set(fingerprint.sanctions_lists)
    directors = set(fingerprint.directors)

    # From OFAC
    for r in ofac_results:
        aliases.update(r.get("aliases", []))
        sanctions_lists.add("OFAC SDN")

    # From UN
    for r in un_results:
        aliases.update(r.get("aliases", []))
        sanctions_lists.add("UN Security Council")

    # From OpenSanctions
    for r in os_results:
        aliases.update(r.get("aliases", []))
        jurisdictions.update(r.get("countries", []))
        sanctions_lists.update(r.get("datasets", []))

    # From OpenCorporates
    for r in corp_results:
        j = r.get("jurisdiction", "")
        if j:
            jurisdictions.add(j)
        cn = r.get("company_number", "")
        if cn:
            fingerprint.registration_numbers.append(
                f"{r.get('jurisdiction', '')}/{cn}"
            )

    # Update fingerprint (deduplicated)
    fingerprint.aliases = sorted(aliases - {fingerprint.canonical_name})
    fingerprint.jurisdictions = sorted(j for j in jurisdictions if j)
    fingerprint.sanctions_lists = sorted(sanctions_lists)
    fingerprint.directors = sorted(directors)

    return fingerprint
