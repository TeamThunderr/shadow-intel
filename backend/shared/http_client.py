import httpx
from backend.shared.logger import get_logger

logger = get_logger(__name__)

_client: httpx.AsyncClient | None = None


async def get_client() -> httpx.AsyncClient:
    global _client
    if _client is None or _client.is_closed:
        _client = httpx.AsyncClient(
            timeout=httpx.Timeout(10.0, connect=5.0),
            follow_redirects=True,
            headers={"User-Agent": "ShadowIntel/1.0"},
        )
    return _client


async def close_client():
    global _client
    if _client and not _client.is_closed:
        await _client.aclose()


async def get_json(url: str, params: dict = None, headers: dict = None, timeout: float = None) -> dict | None:
    client = await get_client()
    try:
        kwargs = {}
        if timeout is not None:
            kwargs["timeout"] = timeout
        resp = await client.get(url, params=params, headers=headers, **kwargs)
        resp.raise_for_status()
        return resp.json()
    except httpx.HTTPStatusError as e:
        logger.warning(f"HTTP {e.response.status_code} from {url}")
        return None
    except Exception as e:
        logger.error(f"Request failed for {url}: {e}")
        return None
