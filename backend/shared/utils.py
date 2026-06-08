import uuid
import time
from functools import wraps
from shared.logger import get_logger

logger = get_logger(__name__)


def generate_entity_id() -> str:
    return str(uuid.uuid4())


def timer(func):
    """Decorator that logs execution time and attaches it to the result."""
    @wraps(func)
    async def wrapper(*args, **kwargs):
        start = time.monotonic()
        result = await func(*args, **kwargs)
        elapsed = int((time.monotonic() - start) * 1000)
        if hasattr(result, "processing_time_ms"):
            result.processing_time_ms = elapsed
        logger.info(f"{func.__name__} completed in {elapsed}ms")
        return result
    return wrapper


async def safe_run(coro, module_name: str):
    """Run a coroutine and return None on failure instead of raising."""
    try:
        return await coro
    except Exception as e:
        logger.error(f"{module_name} failed: {e}")
        return None
