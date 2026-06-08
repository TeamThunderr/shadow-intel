"""
Companies House API Integration

Queries Companies House API for UK company information.
Supports company search, officer/director retrieval, and PSC (Persons of Significant Control) lookup.

API: https://api.company-information.service.gov.uk
Authentication: Basic Auth (API key as username)
Documentation: https://developer.company-information.service.gov.uk/
"""

from typing import Optional, List, Dict, Any
import base64
import asyncio
from backend.shared.http_client import get_json
from backend.shared.logger import get_logger
from backend.shared.config import get_settings

logger = get_logger(__name__)

COMPANIES_HOUSE_BASE = "https://api.company-information.service.gov.uk"
REQUEST_TIMEOUT = 10
MAX_RETRIES = 2
RETRY_DELAY = 1


def _get_auth_header(api_key: str) -> Dict[str, str]:
    """Create Basic Auth header for Companies House API."""
    # Companies House uses API key as username, empty password
    credentials = base64.b64encode(f"{api_key}:".encode()).decode()
    return {"Authorization": f"Basic {credentials}"}


async def search_companies(
    company_name: str,
    limit: int = 10
) -> List[Dict[str, Any]]:
    """
    Search for UK companies by name.
    
    Args:
        company_name: Company name to search
        limit: Maximum results to return
        
    Returns:
        List of company records with company_number and details
    """
    settings = get_settings()
    if not settings.companies_house_api_key:
        logger.warning("No Companies House API key configured — skipping search")
        return []
    
    try:
        logger.info(f"Searching Companies House for: {company_name}")
        
        url = f"{COMPANIES_HOUSE_BASE}/search/companies"
        params = {
            "q": company_name,
            "items_per_page": min(limit, 100),
        }
        
        headers = _get_auth_header(settings.companies_house_api_key)
        data = await _request_with_retry(url, params, headers)
        
        if not data or "items" not in data:
            logger.warning(f"No Companies House results for {company_name}")
            return []
        
        results = []
        for item in data.get("items", [])[:limit]:
            results.append({
                "company_number": item.get("company_number"),
                "name": item.get("title"),
                "type": item.get("company_type"),
                "status": item.get("company_status"),
                "address": item.get("address_snippet"),
                "date_of_creation": item.get("date_of_creation"),
                "source": "companies_house",
                "source_url": f"{COMPANIES_HOUSE_BASE}/company/{item.get('company_number')}",
            })
        
        logger.info(f"Found {len(results)} companies in Companies House")
        return results
        
    except Exception as e:
        logger.error(f"Error searching Companies House: {e}")
        return []


async def get_officers(
    company_number: str,
    include_resigned: bool = False
) -> List[Dict[str, Any]]:
    """
    Get officers/directors for a company.
    
    Args:
        company_number: Companies House company number
        include_resigned: Include resigned officers
        
    Returns:
        List of officer records with names, roles, and appointment dates
    """
    settings = get_settings()
    if not settings.companies_house_api_key:
        logger.warning("No Companies House API key — skipping officers lookup")
        return []
    
    try:
        logger.info(f"Fetching officers for company: {company_number}")
        
        url = f"{COMPANIES_HOUSE_BASE}/company/{company_number}/officers"
        headers = _get_auth_header(settings.companies_house_api_key)
        data = await _request_with_retry(url, headers=headers)
        
        if not data or "items" not in data:
            logger.warning(f"No officers found for {company_number}")
            return []
        
        officers = []
        for item in data.get("items", []):
            # Skip resigned officers if requested
            if not include_resigned and item.get("resigned_on"):
                continue
            
            officers.append({
                "name": item.get("name"),
                "role": item.get("officer_role"),
                "appointed_on": item.get("appointed_on"),
                "resigned_on": item.get("resigned_on"),
                "nationality": item.get("nationality"),
                "date_of_birth": item.get("date_of_birth"),
                "address": item.get("address"),
                "is_active": not bool(item.get("resigned_on")),
                "source": "companies_house",
            })
        
        logger.info(f"Found {len(officers)} officers for {company_number}")
        return officers
        
    except Exception as e:
        logger.error(f"Error fetching officers: {e}")
        return []


async def get_persons_of_significant_control(
    company_number: str
) -> List[Dict[str, Any]]:
    """
    Get Persons of Significant Control (PSC) for a company.
    
    PSCs are individuals or entities with significant control/influence over the company.
    Required disclosure in UK from April 2016 onwards.
    
    Args:
        company_number: Companies House company number
        
    Returns:
        List of PSC records with ownership/control details
    """
    settings = get_settings()
    if not settings.companies_house_api_key:
        logger.warning("No Companies House API key — skipping PSC lookup")
        return []
    
    try:
        logger.info(f"Fetching PSCs for company: {company_number}")
        
        url = f"{COMPANIES_HOUSE_BASE}/company/{company_number}/persons-with-significant-control"
        headers = _get_auth_header(settings.companies_house_api_key)
        data = await _request_with_retry(url, headers=headers)
        
        if not data or "items" not in data:
            logger.warning(f"No PSCs found for {company_number}")
            return []
        
        pscs = []
        for item in data.get("items", []):
            psc = {
                "id": item.get("id"),
                "type": item.get("kind"),  # individual-person-with-significant-control, entity, etc
                "name": item.get("name"),
                "natures_of_control": item.get("natures_of_control", []),
                "notified_on": item.get("notified_on"),
                "ceased_on": item.get("ceased_on"),
                "is_active": not bool(item.get("ceased_on")),
                "source": "companies_house",
            }
            
            # Parse natures of control to extract ownership percentage
            natures = item.get("natures_of_control", [])
            if any("ownership" in nature for nature in natures):
                # Ownership control detected
                ownership_info = next(
                    (n for n in natures if "ownership" in n),
                    None
                )
                if ownership_info:
                    # Extract percentage from nature (e.g., "ownership-of-shares-50-to-75-percent")
                    psc["ownership_percentage"] = _extract_percentage_from_nature(ownership_info)
            
            pscs.append(psc)
        
        logger.info(f"Found {len(pscs)} PSCs for {company_number}")
        return pscs
        
    except Exception as e:
        logger.error(f"Error fetching PSCs: {e}")
        return []


async def get_shareholders(
    company_number: str,
    include_beneficial_owners: bool = True
) -> List[Dict[str, Any]]:
    """
    Get shareholder information for a company.
    
    Combines PSC data with officer data to provide shareholder overview.
    
    Args:
        company_number: Companies House company number
        include_beneficial_owners: Include beneficial owner analysis
        
    Returns:
        List of shareholder records
    """
    try:
        logger.info(f"Fetching shareholders for: {company_number}")
        
        shareholders = []
        
        # Get PSCs (persons of significant control)
        if include_beneficial_owners:
            pscs = await get_persons_of_significant_control(company_number)
            shareholders.extend(pscs)
        
        # Get officers who may also hold shares
        officers = await get_officers(company_number)
        for officer in officers:
            # Add as shareholder if likely (e.g., directors often hold shares)
            shareholders.append({
                "name": officer["name"],
                "type": "officer",
                "role": officer["role"],
                "appointed_on": officer["appointed_on"],
                "is_active": officer["is_active"],
                "source": "companies_house",
            })
        
        logger.info(f"Found {len(shareholders)} shareholders for {company_number}")
        return shareholders
        
    except Exception as e:
        logger.error(f"Error fetching shareholders: {e}")
        return []


def _extract_percentage_from_nature(nature: str) -> Optional[float]:
    """
    Extract ownership percentage from nature of control string.
    
    Examples:
    - "ownership-of-shares-50-to-75-percent" -> 62.5 (midpoint)
    - "ownership-of-shares-more-than-25-percent" -> 50.0 (estimated)
    
    Args:
        nature: Nature of control string
        
    Returns:
        Estimated ownership percentage or None
    """
    try:
        if "100-percent" in nature:
            return 100.0
        elif "75-to-100-percent" in nature:
            return 87.5
        elif "50-to-75-percent" in nature:
            return 62.5
        elif "25-to-50-percent" in nature:
            return 37.5
        elif "more-than-25-percent" in nature or "more-than-50-percent" in nature:
            return 50.0
        elif "less-than-25-percent" in nature:
            return 12.5
    except Exception as e:
        logger.debug(f"Error extracting percentage: {e}")
    
    return None


async def _request_with_retry(
    url: str,
    params: Optional[Dict[str, str]] = None,
    headers: Optional[Dict[str, str]] = None
) -> Optional[Dict[str, Any]]:
    """
    Make HTTP request with retry logic and timeout.
    
    Args:
        url: Request URL
        params: Query parameters
        headers: HTTP headers
        
    Returns:
        Response data or None on failure
    """
    for attempt in range(MAX_RETRIES):
        try:
            result = await get_json(
                url,
                params=params,
                headers=headers,
                timeout=REQUEST_TIMEOUT
            )
            return result
        except asyncio.TimeoutError:
            if attempt < MAX_RETRIES - 1:
                logger.warning(f"Timeout on {url}, retrying...")
                await asyncio.sleep(RETRY_DELAY)
            else:
                logger.error(f"Timeout after {MAX_RETRIES} attempts: {url}")
        except Exception as e:
            if attempt < MAX_RETRIES - 1:
                logger.debug(f"Retry attempt {attempt + 1} for {url}: {e}")
                await asyncio.sleep(RETRY_DELAY)
            else:
                logger.error(f"Error fetching {url}: {e}")
    
    return None
