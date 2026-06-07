from shared.http_client import get_json
from shared.logger import get_logger

logger = get_logger(__name__)

GDELT_BASE = "https://api.gdeltproject.org/api/v2/doc/doc"


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

    result = await get_json(url, params=params)
    if not result:
        return []

    articles = result.get("articles", [])
    news_items = []
    for article in articles:
        news_items.append({
            "title": article.get("title", ""),
            "url": article.get("url", ""),
            "source": article.get("domain", ""),
            "date": article.get("seendate", ""),
            "tone": article.get("tone", 0),
        })

    logger.info(f"GDELT returned {len(news_items)} articles for: {name}")
    return news_items
