"""
OpenCorporates API integration.
World's largest open company database — 200+ million companies.
Free API key: https://opencorporates.com/api_account/new
Docs: https://api.opencorporates.com/documentation/API-Reference
"""

from rapidfuzz import fuzz
from shared.http_client import get_json
from shared.logger import get_logger

logger = get_logger(__name__)

OPENCORPORATES_BASE = "https://api.opencorporates.com/v0.4"
FUZZY_THRESHOLD = 80  # 0-100

# Jurisdictions known for corporate opacity / high financial crime risk
OPACITY_JURISDICTIONS = {
    "VG", "KY", "PA", "SC", "MH", "BZ", "AG",  # BVI, Cayman, Panama, Seychelles, etc.
    "LR", "MU", "BS", "AI", "TC"
}


async def query_opencorporates(name: str, settings) -> list[dict]:
    """
    Search OpenCorporates for companies with similar names.
    Detects entities that may be related to or resurrected from sanctioned companies.
    Works without an API key (anonymous) but at a lower rate limit.
    """
    params: dict = {
        "q": name,
        "per_page": 20,
        "order": "score",
    }
    if settings.opencorporates_api_key:
        params["api_token"] = settings.opencorporates_api_key

    data = await get_json(
        f"{OPENCORPORATES_BASE}/companies/search",
        params=params
    )
    if not data:
        return []

    companies = data.get("results", {}).get("companies", [])
    results = []

    for item in companies:
        company = item.get("company", {})
        company_name = company.get("name", "")
        jurisdiction = company.get("jurisdiction_code", "").upper()
        company_number = company.get("company_number", "")
        status = company.get("current_status", "")
        oc_url = company.get("opencorporates_url", "")
        incorporation_date = company.get("incorporation_date")

        # Calculate name similarity
        similarity = fuzz.token_sort_ratio(name.upper(), company_name.upper())
        if similarity < FUZZY_THRESHOLD:
            continue

        is_opacity = jurisdiction in OPACITY_JURISDICTIONS

        results.append({
            "name": company_name,
            "jurisdiction": jurisdiction,
            "company_number": company_number,
            "status": status,
            "incorporation_date": incorporation_date,
            "url": oc_url,
            "similarity": round(similarity / 100, 3),
            "opacity_jurisdiction": is_opacity,
            "source": "OpenCorporates",
        })

    logger.info(f"OpenCorporates: {len(results)} matches for '{name}'")
    return results


async def get_company_officers(jurisdiction: str, company_number: str, settings) -> list[dict]:
    """
    Fetch officers (directors) for a specific company.
    Used to detect director overlaps with sanctioned entities.
    """
    params: dict = {}
    if settings.opencorporates_api_key:
        params["api_token"] = settings.opencorporates_api_key

    data = await get_json(
        f"{OPENCORPORATES_BASE}/companies/{jurisdiction}/{company_number}/officers",
        params=params
    )
    if not data:
        return []

    officers = data.get("results", {}).get("officers", [])
    return [
        {
            "name": o.get("officer", {}).get("name", ""),
            "position": o.get("officer", {}).get("position", ""),
            "start_date": o.get("officer", {}).get("start_date"),
            "end_date": o.get("officer", {}).get("end_date"),
        }
        for o in officers
    ]
