import logging
import httpx
import pycountry
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)

async def parse_fatf_jurisdictions() -> list[dict]:
    """
    Returns the FATF high-risk country list as structured data.
    
    Try scraping first. Fall back to hardcoded list if scraping fails.
    """
    results = []
    
    try:
        # STEP 1: Try scraping
        async with httpx.AsyncClient(timeout=15) as client:
            response = await client.get("https://www.fatf-gafi.org/en/countries/black-and-grey-lists.html")
            response.raise_for_status()
            
            soup = BeautifulSoup(response.text, "html.parser")
            
            blacklist_countries = []
            greylist_countries = []
            
            # Simple heuristic for scraping based on headings and subsequent lists
            for header in soup.find_all(['h2', 'h3']):
                header_text = header.get_text(strip=True).lower()
                if "call for action" in header_text:
                    ul = header.find_next_sibling('ul')
                    if ul:
                        for li in ul.find_all('li'):
                            blacklist_countries.append(li.get_text(strip=True))
                elif "increased monitoring" in header_text:
                    ul = header.find_next_sibling('ul')
                    if ul:
                        for li in ul.find_all('li'):
                            greylist_countries.append(li.get_text(strip=True))
            
            if len(blacklist_countries) + len(greylist_countries) < 5:
                raise ValueError("Scraping returned fewer than 5 countries")
                
            for country in blacklist_countries:
                iso2 = None
                try:
                    match = pycountry.countries.search_fuzzy(country)
                    if match:
                        iso2 = match[0].alpha_2
                except Exception:
                    pass
                results.append({
                    "country": country,
                    "iso2": iso2,
                    "risk_level": "blacklist",
                    "risk_score": 1.0,
                    "source": "fatf_scraped"
                })
                
            for country in greylist_countries:
                iso2 = None
                try:
                    match = pycountry.countries.search_fuzzy(country)
                    if match:
                        iso2 = match[0].alpha_2
                except Exception:
                    pass
                results.append({
                    "country": country,
                    "iso2": iso2,
                    "risk_level": "greylist",
                    "risk_score": 0.65,
                    "source": "fatf_scraped"
                })

    except Exception as e:
        logger.warning(f"Failed to scrape FATF list: {e}. Falling back to hardcoded list.")
        results = []  # Clear any partial scraped data
        
        # STEP 2: Fallback hardcoded list
        blacklist = [
            "North Korea", "Iran", "Myanmar"
        ]
        
        greylist = [
            "Bulgaria", "Burkina Faso", "Cameroon", "Croatia",
            "Democratic Republic of Congo", "Haiti", "Kenya", "Mali",
            "Monaco", "Mozambique", "Namibia", "Nigeria", "Philippines",
            "Senegal", "South Africa", "Syria", "Tanzania", "Venezuela",
            "Vietnam", "Yemen"
        ]
        
        for country in blacklist:
            iso2 = None
            try:
                match = pycountry.countries.search_fuzzy(country)
                if match:
                    iso2 = match[0].alpha_2
            except Exception:
                pass
                
            results.append({
                "country": country,
                "iso2": iso2,
                "risk_level": "blacklist",
                "risk_score": 1.0,
                "source": "fatf_hardcoded"
            })
            
        for country in greylist:
            iso2 = None
            try:
                match = pycountry.countries.search_fuzzy(country)
                if match:
                    iso2 = match[0].alpha_2
            except Exception:
                pass
                
            results.append({
                "country": country,
                "iso2": iso2,
                "risk_level": "greylist",
                "risk_score": 0.65,
                "source": "fatf_hardcoded"
            })
            
    return results

if __name__ == "__main__":
    import asyncio
    # Simple standalone test
    result = asyncio.run(parse_fatf_jurisdictions())
    print(f"Got {len(result)} countries")
    print(result[:3])
