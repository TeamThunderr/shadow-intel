import asyncio
import httpx
from datetime import datetime
from typing import Optional
from shared.http_client import get_client
from shared.logger import get_logger

logger = get_logger(__name__)

GDELT_BASE = "https://api.gdeltproject.org/api/v2/doc/doc"

# Global rate limiting semaphore for external APIs
api_semaphore = asyncio.Semaphore(5)


def parse_gdelt_date(date_str: str) -> Optional[datetime]:
    """
    Parses GDELT seendate string (usually YYYYMMDDHHMMSS or with separators)
    into a datetime object.
    """
    if not date_str:
        return None
    # Extract digits only
    clean_str = "".join([c for c in date_str if c.isdigit()])
    if len(clean_str) >= 8:
        try:
            year = int(clean_str[0:4])
            month = int(clean_str[4:6])
            day = int(clean_str[6:8])
            hour = int(clean_str[8:10]) if len(clean_str) >= 10 else 0
            minute = int(clean_str[10:12]) if len(clean_str) >= 12 else 0
            second = int(clean_str[12:14]) if len(clean_str) >= 14 else 0
            return datetime(year, month, day, hour, minute, second)
        except Exception:
            pass
    return None


async def search_gdelt(name: str, days: int = 30) -> list[dict]:
    """
    Search GDELT news database for recent mentions of an entity.
    GDELT indexes global news in near-real-time. No API key required.
    """
    url = GDELT_BASE
    params = {
        "query": f'"{name}"',
        "mode": "artlist",
        "maxrecords": 25,
        "format": "json",
        "timespan": f"{days}d",
    }

    logger.info(f"Querying GDELT for: {name}")
    
    max_retries = 3
    attempt = 0
    backoff = 1.0  # Initial sleep time in seconds
    result = None
    
    while attempt <= max_retries:
        try:
            async with api_semaphore:
                client = await get_client()
                resp = await client.get(url, params=params, timeout=15.0)
                
                if resp.status_code == 429:
                    attempt += 1
                    if attempt > max_retries:
                        logger.error(f"GDELT query '{name}' rate limited after {max_retries} retries.")
                        return []
                    
                    retry_after = resp.headers.get("Retry-After")
                    sleep_time = backoff
                    if retry_after:
                        try:
                            sleep_time = float(retry_after)
                        except ValueError:
                            pass
                    
                    logger.warning(
                        f"GDELT query '{name}' rate limited (429). "
                        f"Retry attempt {attempt}/{max_retries} after {sleep_time:.1f}s."
                    )
                    await asyncio.sleep(sleep_time)
                    backoff *= 2.0  # Exponential backoff
                    continue
                
                resp.raise_for_status()
                result = resp.json()
                break  # Success!
                
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 429:
                attempt += 1
                if attempt > max_retries:
                    logger.error(f"GDELT query '{name}' rate limited after {max_retries} retries.")
                    return []
                
                retry_after = e.response.headers.get("Retry-After")
                sleep_time = backoff
                if retry_after:
                    try:
                        sleep_time = float(retry_after)
                    except ValueError:
                        pass
                logger.warning(
                    f"GDELT query '{name}' rate limited (429) via status error. "
                    f"Retry attempt {attempt}/{max_retries} after {sleep_time:.1f}s."
                )
                await asyncio.sleep(sleep_time)
                backoff *= 2.0
                continue
            else:
                logger.error(f"GDELT HTTP status error: {e.response.status_code} for query '{name}'")
                return []
        except httpx.TimeoutException:
            logger.error(f"GDELT connection timed out for query '{name}'")
            return []
        except Exception as e:
            logger.error(f"GDELT request failed for query '{name}': {e}")
            return []
            
    if result is None:
        return []

    articles = result.get("articles", [])
    news_items = []
    
    # Calculate match confidence for GDELT based on name match
    from rapidfuzz import fuzz
    from fabric.pipeline import normalize_entity_name
    q_norm = normalize_entity_name(name)
    
    for article in articles:
        try:
            title = article.get("title", "")
            domain = article.get("domain", "")
            url_val = article.get("url", "")
            date_str = article.get("seendate", "")
            lang = article.get("language", "English")
            
            # Parse tone
            tone_val = article.get("tone", 0.0)
            try:
                tone = float(tone_val)
            except Exception:
                tone = 0.0
                
            published_date = parse_gdelt_date(date_str)
            
            # Entity matching confidence
            # Use fuzz match on title to see if query is mentioned in title
            # If so, high confidence (e.g. 0.90), otherwise default to 0.70
            confidence = 0.70
            if q_norm:
                title_norm = title.lower()
                if q_norm.lower() in title_norm:
                    confidence = 0.90
                    
            news_items.append({
                "source": domain or "GDELT",
                "title": title,
                "url": url_val,
                "entity": name,
                "country": "unknown",
                "summary": f"GDELT News. Domain: {domain}. Language: {lang}. Tone: {tone}.",
                "confidence": confidence,
                "published_date": published_date,
                "language": lang,
                "tone": tone
            })
        except Exception as pe:
            logger.warning(f"Error parsing GDELT article item: {pe}")

    logger.info(f"GDELT returned {len(news_items)} articles for: {name}")
    return news_items
