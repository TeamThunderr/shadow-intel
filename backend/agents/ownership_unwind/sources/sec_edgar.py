"""
SEC EDGAR API Integration

Queries SEC EDGAR (Electronic Data Gathering, Organization, and Retrieval) for US company ownership information.
Supports company search, beneficial ownership filing retrieval (Schedule 13D/13G), and UBO detection.

API: https://data.sec.gov
Documentation: https://www.sec.gov/edgar/API-reference
"""

from typing import Optional, List, Dict, Any
import asyncio
import re
import html
from backend.shared.http_client import get_json, get_client
from backend.shared.logger import get_logger

logger = get_logger(__name__)

EDGAR_BASE = "https://data.sec.gov"
EDGAR_SEARCH_BASE = "https://www.sec.gov/cgi-bin/browse-edgar"
REQUEST_TIMEOUT = 10
MAX_RETRIES = 2
RETRY_DELAY = 1

# In-memory cache for company ticker mapping to CIK
_ticker_map: Optional[Dict[str, Any]] = None


def is_likely_person(name: str) -> bool:
    """
    Heuristically determine if a name is likely a natural person or a corporate entity.
    """
    if not name:
        return False
        
    name_upper = name.upper()
    
    # Common corporate designators / entity keywords
    corporate_keywords = [
        r"\bINC\b", r"\bINCORPORATED\b",
        r"\bLTD\b", r"\bLIMITED\b",
        r"\bCO\b", r"\bCOMPANY\b", r"\bCOMPANIES\b",
        r"\bCORP\b", r"\bCORPORATION\b",
        r"\bLLC\b", r"\bL\.L\.C\.\b",
        r"\bLP\b", r"\bL\.P\.\b", r"\bLLP\b", r"\bL\.L\.P\.\b",
        r"\bTRUST\b", r"\bFUND\b", r"\bFUNDS\b",
        r"\bPARTNERS\b", r"\bPARTNERSHIP\b",
        r"\bCAPITAL\b", r"\bMANAGEMENT\b", r"\bHOLDINGS\b", r"\bHOLDING\b",
        r"\bGROUP\b", r"\bPLC\b", r"\bP\.L\.C\.\b",
        r"\bASSOCIATES\b", r"\bASSOCIATION\b",
        r"\bBANK\b", r"\bINSURANCE\b", r"\bSYSTEM\b", r"\bSYSTEMS\b",
        r"\bFINANCIAL\b", r"\bINVESTMENTS\b", r"\bINVESTMENT\b",
        r"\bFOUNDATION\b", r"\bADVISERS\b", r"\bADVISORS\b",
        r"\bSERVICES\b", r"\bSECURITIES\b", r"\bVENTURES\b",
        r"\bBLACKROCK\b", r"\bVANGUARD\b", r"\bFIDELITY\b", r"\bSTATE STREET\b",
        r"\bGOLDMAN SACHS\b", r"\bMORGAN STANLEY\b", r"\bJPMORGAN\b",
        r"\bCITIGROUP\b", r"\bNOMURA\b", r"\bDEUTSCHE BANK\b", r"\bBARCLAYS\b",
        r"\bBNP PARIBAS\b", r"\bHSBC\b"
    ]
    
    # Check if any corporate keywords are present
    for pattern in corporate_keywords:
        if re.search(pattern, name_upper):
            return False
            
    # Also if the name starts with "THE ", it's usually an entity (like "The Vanguard Group")
    if name_upper.startswith("THE "):
        return False
        
    return True


def _clean_name(name: str) -> str:
    """Clean up extracted name by removing extra whitespaces, newlines, and trailing commas/punctuation."""
    if not name:
        return ""
    # Replace multiple spaces/newlines/tabs with single space
    name = re.sub(r'\s+', ' ', name)
    # Strip leading/trailing whitespaces and characters like commas, semicolons, quotes
    name = name.strip(" ,;\"'()[]{}")
    return name


def is_boilerplate_line(line: str) -> bool:
    """Check if a line matches SEC form instruction or boilerplate formatting."""
    if not line:
        return True
    
    line_upper = line.upper()
    
    # 1. Check for checkbox indicators in the raw line
    if re.search(r'\[\s*[xX_\s]?\s*\]', line):
        return True
        
    if re.search(r'\(\s*[xX_\s]?\s*\)', line):
        return True
        
    if '[' in line or ']' in line:
        return True
        
    # 2. Check for common SEC form field labels/headings using word boundaries
    boilerplate_keywords = [
        r"\bCHECK THE APPROPRIATE BOX\b",
        r"\bMEMBER OF A GROUP\b",
        r"\bSEC USE ONLY\b",
        r"\bI\.R\.S\.\b",
        r"\bIDENTIFICATION\b",
        r"\bCITIZENSHIP\b",
        r"\bPLACE OF ORGANIZATION\b",
        r"\bSOLE VOTING\b",
        r"\bSHARED VOTING\b",
        r"\bSOLE DISPOSITIVE\b",
        r"\bSHARED DISPOSITIVE\b",
        r"\bAGGREGATE AMOUNT\b",
        r"\bPERCENT OF CLASS\b",
        r"\bTYPE OF REPORTING\b",
        r"\bCUSIP\b",
        r"\bSCHEDULE\s*13[DG]?(?:/A)?\b",
        r"\bFILED BY\b",
        r"\bFILED WITH\b",
        r"^EXHIBIT\s+[\d\w\-\.]+$",
        r"^EXHIBIT$",
        r"^SIGNATURES?$",
        r"\bDATE OF EVENT\b",
        r"\bTITLE OF CLASS\b",
        r"\bNAMES? OF REPORTING\b",
        r"\bCHECK BOX\b",
        r"\bCHECK IF THE\b",
        r"\bROW \d+\b",
        r"\bROW\s*\(\d+\)",
        r"\bITEM \d+\b",
        r"\bPAGE \d+\b",
        r"\bPAGE \d+ OF \d+\b",
        r"\bBOX IF A MEMBER\b",
        r"\bBENEFICIALLY OWNED\b",
        r"\bCLASS OF SECURITIES\b",
        r"\bINSTRUCTIONS FOR\b",
        r"^INSTRUCTIONS?$",
        r"\bATTENTION\s*:\b",
        r"\bINTENTIONAL MISSTATEMENTS\b",
        r"\bOMISSIONS OF FACT\b",
        r"\bRULE 13D\b",
        r"\bRULE 13G\b",
        r"\bRULE 13D-\d+\b",
        r"\bSECURITIES AND EXCHANGE COMMISSION\b",
        r"\bWASHINGTON,\s*D\.C\.\b",
        r"\bUNDER THE SECURITIES\b",
        r"^AMENDMENT\s+\d+$",
        r"^AMENDMENT$",
        r"\bBY:\s*/S/\b",
        r"\b/S/\b",
        r"\bUNDERSIGNED\b",
        r"\bKNOWLEDGE AND BELIEF\b",
        r"\bREASONABLE INQUIRY\b",
        r"\bJOINT FILING AGREEMENT\b",
        r"\bFILING AGREEMENT\b",
        r"\bOF THE ABOVE\b",
        r"\bENTITIES ONLY\b",
        r"\bCLASS PERCENT\b",
        r"\bREPORTING PERSONS?\b",
        r"\bSUBJECT COMPAN(Y|IES)\b",
        r"\bPURSUANT TO\b"
    ]
    
    for pattern in boilerplate_keywords:
        if re.search(pattern, line_upper):
            return True
            
    # Check if line matches a list index like (a), (b), (1), (2) at the start or is just a single char/number
    cleaned_temp = line.strip(" ,;\"'()[]{}")
    if len(cleaned_temp) < 3:
        return True
        
    return False


def is_jurisdiction_or_state(name: str) -> bool:
    """Check if the extracted name is actually a state or country/jurisdiction."""
    name_upper = name.upper()
    jurisdictions = {
        # States
        "ALABAMA", "ALASKA", "ARIZONA", "ARKANSAS", "CALIFORNIA", "COLORADO", "CONNECTICUT", "DELAWARE",
        "FLORIDA", "GEORGIA", "HAWAII", "IDAHO", "ILLINOIS", "INDIANA", "IOWA", "KANSAS", "KENTUCKY",
        "LOUISIANA", "MAINE", "MARYLAND", "MASSACHUSETTS", "MICHIGAN", "MINNESOTA", "MISSISSIPPI",
        "MISSOURI", "MONTANA", "NEBRASKA", "NEVADA", "NEW HAMPSHIRE", "NEW JERSEY", "NEW MEXICO",
        "NEW YORK", "NORTH CAROLINA", "NORTH DAKOTA", "OHIO", "OKLAHOMA", "OREGON", "PENNSYLVANIA",
        "RHODE ISLAND", "SOUTH CAROLINA", "SOUTH DAKOTA", "TENNESSEE", "TEXAS", "UTAH", "VERMONT",
        "VIRGINIA", "WASHINGTON", "WEST VIRGINIA", "WISCONSIN", "WYOMING",
        # Countries / Offshore
        "UNITED STATES", "U.S.A.", "USA", "UNITED STATES OF AMERICA",
        "UNITED KINGDOM", "U.K.", "UK", "GREAT BRITAIN",
        "CAYMAN ISLANDS", "CAYMAN", "BRITISH VIRGIN ISLANDS", "BVI", "B.V.I.",
        "BERMUDA", "JERSEY", "GUERNSEY", "LUXEMBOURG", "SWITZERLAND",
        "SINGAPORE", "HONG KONG", "CANADA", "GERMANY", "FRANCE", "JAPAN",
        "NETHERLANDS", "IRELAND"
    }
    return name_upper in jurisdictions


def _is_valid_owner_name(name: str, raw_line: str = "") -> bool:
    """
    Determine if the extracted name is a valid person or organization,
    and filter out filing instructions, form labels, checkboxes, boilerplate text.
    """
    if not name:
        return False
        
    # If raw line was provided, do boilerplate check on raw line first
    if raw_line and is_boilerplate_line(raw_line):
        return False
        
    # Also do boilerplate check on name itself
    if is_boilerplate_line(name):
        return False
        
    name_upper = name.upper()
    
    # Check if the name starts with common signature labels
    if name_upper.startswith("BY:") or name_upper.startswith("BY "):
        return False
        
    if name_upper.startswith("TITLE:") or name_upper.startswith("TITLE "):
        return False
    if name_upper.startswith("DATE:") or name_upper.startswith("DATE ") or name_upper.startswith("DATED:") or name_upper.startswith("DATED "):
        return False
    if name_upper.startswith("NAME:") or name_upper.startswith("NAME "):
        return False
    if name_upper.startswith("ATTENTION:") or name_upper.startswith("ATTENTION :"):
        return False
    if name_upper.startswith("NOTE:") or name_upper.startswith("NOTE :"):
        return False
        
    # Check for instruction prefixes
    for prefix in ["INSTRUCTION ", "INSTRUCTIONS ", "INSTRUCTION.", "INSTRUCTIONS.", "INSTRUCTION:", "INSTRUCTIONS:"]:
        if name_upper.startswith(prefix):
            return False
        
    # Check if the name contains signature indicator /s/
    if "/S/" in name_upper:
        return False
        
    # Check if name is a jurisdiction/state
    if is_jurisdiction_or_state(name):
        return False
        
    # Length or numeric/punctuation check
    if len(name) < 3:
        return False
        
    if re.match(r'^[\d\s\W_]+$', name):
        return False
        
    if "?" in name or "..." in name or "___" in name:
        return False
        
    return True



def _normalize_for_search(name: str) -> str:
    """Normalize company name for robust search matching by stripping suffixes and punctuation."""
    if not name:
        return ""
    n = name.lower()
    # Remove punctuation
    n = re.sub(r'[^\w\s]', '', n)
    # Remove common corporate suffixes
    suffixes = [
        r'\binc\b', r'\bincorporated\b', r'\bltd\b', r'\blimited\b',
        r'\bcorp\b', r'\bcorporation\b', r'\bco\b', r'\bcompany\b',
        r'\bllc\b', r'\bplc\b'
    ]
    for s in suffixes:
        n = re.sub(s, '', n)
    return ' '.join(n.split())



async def _load_ticker_map() -> Dict[str, Any]:
    """Load the master SEC company ticker mapping JSON."""
    global _ticker_map
    if _ticker_map is not None:
        return _ticker_map

    url = "https://www.sec.gov/files/company_tickers.json"
    try:
        # SEC requires a descriptive User-Agent
        headers = {"User-Agent": "Shadow-Intel/1.0 libin@example.com"}
        data = await _request_with_retry(url, headers=headers)
        if data:
            _ticker_map = data
            logger.info("SEC ticker map loaded successfully")
            return _ticker_map
    except Exception as e:
        logger.error(f"Error loading SEC ticker map: {e}")

    return {}


async def search_companies(
    company_name: str,
    limit: int = 10
) -> List[Dict[str, Any]]:
    """
    Search for US companies by name in SEC EDGAR.
    
    Args:
        company_name: Company name or ticker symbol to search
        limit: Maximum results to return
        
    Returns:
        List of company records with CIK and details
    """
    try:
        logger.info(f"Searching SEC EDGAR for: {company_name}")
        ticker_map = await _load_ticker_map()
        if not ticker_map:
            return []

        results = []
        company_name_lower = company_name.lower()
        company_name_norm = _normalize_for_search(company_name)

        for item in ticker_map.values():
            title = item.get("title", "")
            ticker = item.get("ticker", "")
            cik = item.get("cik_str")

            title_norm = _normalize_for_search(title)
            # Match if normalized company name is in normalized title, or exact ticker match
            if (company_name_norm and company_name_norm in title_norm) or company_name_lower == ticker.lower():
                cik_str = str(cik).zfill(10)
                results.append({
                    "cik": cik_str,
                    "name": title,
                    "ticker": ticker,
                    "source": "sec_edgar",
                    "source_url": f"https://www.sec.gov/edgar/browse/?CIK={cik_str}",
                })
                if len(results) >= limit:
                    break

        logger.info(f"Found {len(results)} matching companies in SEC EDGAR")
        return results

    except Exception as e:
        logger.error(f"Error searching SEC EDGAR: {e}")
        return []


async def search_company_filings(
    cik: str,
    form_types: Optional[List[str]] = None,
    limit: int = 50
) -> List[Dict[str, Any]]:
    """
    Search for specific SEC filings for a company.
    
    Args:
        cik: SEC Central Index Key (company identifier)
        form_types: List of form types (e.g., ['13D', '13G', '10-K'])
        limit: Maximum filings to return
        
    Returns:
        List of filing records
    """
    try:
        if not form_types:
            form_types = ["13D", "13D/A", "13G", "13G/A", "SC 13D", "SC 13D/A", "SC 13G", "SC 13G/A"]

        # Ensure CIK is zero-padded
        cik_padded = str(cik).zfill(10)
        logger.info(f"Searching filings for CIK {cik_padded}, forms: {form_types}")

        url = f"{EDGAR_BASE}/submissions/CIK{cik_padded}.json"
        headers = {"User-Agent": "Shadow-Intel/1.0 libin@example.com"}
        data = await _request_with_retry(url, headers=headers)

        if not data or "filings" not in data:
            logger.warning(f"No filings found for CIK {cik_padded}")
            return []

        recent = data.get("filings", {}).get("recent", {})
        if not recent:
            return []

        filings = []
        for i in range(len(recent.get("accessionNumber", []))):
            form = recent.get("form", [])[i]
            if form not in form_types:
                continue

            acc_num = recent.get("accessionNumber", [])[i]
            filing_date = recent.get("filingDate", [])[i]
            primary_doc = recent.get("primaryDocument", [])[i]

            acc_num_no_dash = acc_num.replace("-", "")
            cik_clean = str(int(cik))
            source_url = f"https://www.sec.gov/Archives/edgar/data/{cik_clean}/{acc_num_no_dash}/{primary_doc}"

            filings.append({
                "form_type": form,
                "filing_date": filing_date,
                "accession_number": acc_num,
                "cik": cik_padded,
                "source": "sec_edgar",
                "source_url": source_url,
                "primary_document": primary_doc
            })

            if len(filings) >= limit:
                break

        logger.info(f"Found {len(filings)} filings matching forms for CIK {cik_padded}")
        return filings

    except Exception as e:
        logger.error(f"Error searching filings: {e}")
        return []


async def _parse_filing(
    accession_number: str,
    cik: str,
    primary_doc: str,
    filing_type: str
) -> Optional[List[Dict[str, Any]]]:
    """
    Download and parse Schedule 13D or 13G document.
    Extracts reporting person names and percentage stakes.
    """
    try:
        acc_num_no_dash = accession_number.replace("-", "")
        cik_clean = str(int(cik))
        url = f"https://www.sec.gov/Archives/edgar/data/{cik_clean}/{acc_num_no_dash}/{primary_doc}"

        logger.info(f"Fetching raw filing from {url}")
        headers = {"User-Agent": "Shadow-Intel/1.0 libin@example.com"}
        content = await _request_text_with_retry(url, headers=headers)
        if not content:
            return None

        owners = []

        # 1. XML Cover Page parsing (Standard for December 2024 onwards)
        if "xml" in primary_doc.lower() or "<edgarSubmission" in content:
            # Locate all reporting person blocks
            blocks = re.findall(r'<coverPageHeaderReportingPersonDetails>.*?</coverPageHeaderReportingPersonDetails>', content, re.DOTALL)
            if not blocks:
                blocks = re.findall(r'<coverPageHeaderReportingPerson.*?>.*?</coverPageHeaderReportingPerson.*?>', content, re.DOTALL)

            for block in blocks:
                name_match = re.search(r'<reportingPersonName>(.*?)</reportingPersonName>', block)
                percent_match = re.search(r'<classPercent>(.*?)</classPercent>', block)
                if name_match:
                    name = name_match.group(1).strip()
                    # Clean XML entities if any
                    name = re.sub(r'&amp;', '&', name)
                    percent = None
                    if percent_match:
                        try:
                            percent = float(percent_match.group(1).strip())
                        except ValueError:
                            pass
                    owners.append({
                        "name": name,
                        "ownership_percentage": percent,
                        "type": "person" if is_likely_person(name) else "entity",
                        "source": "sec_edgar",
                        "filing_type": filing_type,
                        "accession_number": accession_number,
                        "source_url": url
                    })

        # 2. Text / HTML heuristic fallback (Standard for older legacy files)
        if not owners:
            # Decode HTML entities first
            content_decoded = html.unescape(content)
            # Replace common white-space entities like non-breaking spaces
            content_decoded = content_decoded.replace('\xa0', ' ')
            # Strip tags for plain text heuristic matching
            text_content = re.sub(r'<[^>]+>', '\n', content_decoded)
            lines = [line.strip() for line in text_content.split('\n') if line.strip()]

            names = []
            percentages = []

            for i, line in enumerate(lines):
                # Search for Reporting Person Name patterns
                if "NAMES OF REPORTING PERSONS" in line.upper() or "NAME OF REPORTING PERSON" in line.upper():
                    # Check if the name is on the same line after the keyword (e.g. "(1)Names of reporting persons. BlackRock, Inc.")
                    match = re.search(r'(?:NAMES? OF REPORTING PERSONS?)(?:[\.\s\d\)]+)?[\.\s\:]+(.+)$', line, re.IGNORECASE)
                    if match:
                        candidate = match.group(1).strip()
                        clean_c = _clean_name(candidate)
                        if _is_valid_owner_name(clean_c, candidate):
                            names.append(clean_c)
                            continue
                            
                    for j in range(i + 1, min(i + 8, len(lines))):
                        candidate = lines[j].strip()
                        if not candidate or len(candidate) < 2:
                            continue
                        clean_c = _clean_name(candidate)
                        if _is_valid_owner_name(clean_c, candidate):
                            names.append(clean_c)
                            break

                # Search for Ownership Percentage patterns
                if "PERCENT OF CLASS REPRESENTED" in line.upper() or "PERCENT OF CLASS" in line.upper():
                    for j in range(i + 1, min(i + 8, len(lines))):
                        candidate = lines[j].strip()
                        if not candidate or len(candidate) < 2:
                            continue
                        percent_match = re.search(r'(\d+(?:\.\d+)?)\s*%', candidate)
                        if percent_match:
                            percentages.append(float(percent_match.group(1)))
                            break

            for k, name in enumerate(names):
                percent = percentages[k] if k < len(percentages) else None
                owners.append({
                    "name": name,
                    "ownership_percentage": percent,
                    "type": "person" if is_likely_person(name) else "entity",
                    "source": "sec_edgar",
                    "filing_type": filing_type,
                    "accession_number": accession_number,
                    "source_url": url
                })

        return owners if owners else None

    except Exception as e:
        logger.error(f"Error parsing filing {accession_number}: {e}")
        return None


async def get_beneficial_owners_13d(
    cik: str
) -> List[Dict[str, Any]]:
    """
    Extract beneficial owners from Schedule 13D filings.
    
    Schedule 13D: Used when acquiring > 5% beneficial ownership.
    
    Args:
        cik: SEC Central Index Key
        
    Returns:
        List of beneficial owners extracted from 13D filings
    """
    try:
        logger.info(f"Extracting beneficial owners from 13D filings: {cik}")
        filings = await search_company_filings(
            cik,
            form_types=["13D", "13D/A", "SC 13D", "SC 13D/A"],
            limit=5
        )

        owners = []
        seen_names = set()
        for filing in filings:
            parsed = await _parse_filing(
                filing.get("accession_number"),
                cik,
                filing.get("primary_document"),
                "13D"
            )
            if parsed:
                valid_parsed = []
                for owner in parsed:
                    name = owner.get("name")
                    if not name or not _is_valid_owner_name(name):
                        continue
                    clean_n = _clean_name(name)
                    pct = owner.get("ownership_percentage")
                    # Filter out sub-threshold ownership (< 5%)
                    if pct is not None and pct < 5.0:
                        continue
                    owner["name"] = clean_n
                    valid_parsed.append(owner)

                for owner in valid_parsed:
                    name_lower = owner["name"].lower()
                    if name_lower in seen_names:
                        continue
                    seen_names.add(name_lower)
                    owner["filing_date"] = filing.get("filing_date")
                    owners.append(owner)

        logger.info(f"Extracted {len(owners)} beneficial owners from 13D")
        return owners

    except Exception as e:
        logger.error(f"Error extracting 13D beneficial owners: {e}")
        return []


async def get_beneficial_owners_13g(
    cik: str
) -> List[Dict[str, Any]]:
    """
    Extract beneficial owners from Schedule 13G filings.
    
    Schedule 13G: Simplified version of 13D for passive investors.
    
    Args:
        cik: SEC Central Index Key
        
    Returns:
        List of beneficial owners from 13G filings
    """
    try:
        logger.info(f"Extracting beneficial owners from 13G filings: {cik}")
        filings = await search_company_filings(
            cik,
            form_types=["13G", "13G/A", "SC 13G", "SC 13G/A"],
            limit=5
        )

        owners = []
        seen_names = set()
        for filing in filings:
            parsed = await _parse_filing(
                filing.get("accession_number"),
                cik,
                filing.get("primary_document"),
                "13G"
            )
            if parsed:
                valid_parsed = []
                for owner in parsed:
                    name = owner.get("name")
                    if not name or not _is_valid_owner_name(name):
                        continue
                    clean_n = _clean_name(name)
                    pct = owner.get("ownership_percentage")
                    # Filter out sub-threshold ownership (< 5%)
                    if pct is not None and pct < 5.0:
                        continue
                    owner["name"] = clean_n
                    valid_parsed.append(owner)

                for owner in valid_parsed:
                    name_lower = owner["name"].lower()
                    if name_lower in seen_names:
                        continue
                    seen_names.add(name_lower)
                    owner["filing_date"] = filing.get("filing_date")
                    owners.append(owner)

        logger.info(f"Extracted {len(owners)} beneficial owners from 13G")
        return owners

    except Exception as e:
        logger.error(f"Error extracting 13G beneficial owners: {e}")
        return []


async def get_company_facts(cik: str) -> Optional[Dict[str, Any]]:
    """Get company facts and financial data from SEC EDGAR."""
    try:
        cik_padded = str(cik).zfill(10)
        logger.info(f"Fetching company facts for CIK: {cik_padded}")

        url = f"{EDGAR_BASE}/api/xbrl/companyfacts/CIK{cik_padded}.json"
        headers = {"User-Agent": "Shadow-Intel/1.0 libin@example.com"}
        data = await _request_with_retry(url, headers=headers)
        return data

    except Exception as e:
        logger.error(f"Error fetching company facts: {e}")
        return None


async def _parse_13d_filing(
    accession_number: str,
    cik: str
) -> Optional[Dict[str, Any]]:
    """Legacy parser stub - redirected to main parser."""
    filings = await search_company_filings(cik, form_types=["13D", "13D/A", "SC 13D", "SC 13D/A"], limit=5)
    for f in filings:
        if f.get("accession_number") == accession_number:
            parsed = await _parse_filing(accession_number, cik, f.get("primary_document"), "13D")
            return parsed[0] if parsed else None
    return None


async def _parse_13g_filing(
    accession_number: str,
    cik: str
) -> Optional[Dict[str, Any]]:
    """Legacy parser stub - redirected to main parser."""
    filings = await search_company_filings(cik, form_types=["13G", "13G/A", "SC 13G", "SC 13G/A"], limit=5)
    for f in filings:
        if f.get("accession_number") == accession_number:
            parsed = await _parse_filing(accession_number, cik, f.get("primary_document"), "13G")
            return parsed[0] if parsed else None
    return None


async def _request_with_retry(
    url: str,
    params: Optional[Dict[str, str]] = None,
    headers: Optional[Dict[str, str]] = None
) -> Optional[Dict[str, Any]]:
    """Make JSON HTTP request with retry logic and timeout."""
    headers = headers or {}
    headers["User-Agent"] = "Shadow-Intel/1.0 libin@example.com"

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


async def _request_text_with_retry(
    url: str,
    headers: Optional[Dict[str, str]] = None
) -> Optional[str]:
    """Make text/HTML HTTP request with retry logic and timeout."""
    headers = headers or {}
    headers["User-Agent"] = "Shadow-Intel/1.0 libin@example.com"

    for attempt in range(MAX_RETRIES):
        try:
            client = await get_client()
            resp = await client.get(url, headers=headers, timeout=REQUEST_TIMEOUT)
            resp.raise_for_status()
            return resp.text
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
